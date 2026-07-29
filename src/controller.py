# src/controller.py

from __future__ import annotations

import queue
import threading
from typing import Any, Optional


WAKE_EVENT = "wake"
ANSWER_FINISHED_EVENT = "answer_finished"


class StudyBuddyController:
    """
    Coordinates wake-word detection, STT, RAG, and TTS.

    Wake-word detection runs in a background thread.

    Each biology question is answered in its own worker thread.
    """

    def __init__(
        self,
        wake_word_detector: Any,
        speech_to_text: Any,
        tts: Any,
        assistant: Optional[Any] = None,
        follow_up_wait_seconds: float = 4.0,
    ) -> None:
        self.wake_word_detector = wake_word_detector
        self.speech_to_text = speech_to_text
        self.tts = tts

        # ==================== RAG REFERENCE ====================
        # assistant will be None until the RAG system is enabled.
        self.assistant = assistant
        # ================== END RAG REFERENCE ==================

        self.follow_up_wait_seconds = follow_up_wait_seconds

        self.events: queue.Queue[
            tuple[str, Optional[int]]
        ] = queue.Queue()

        self.shutdown_event = threading.Event()

        # When set, the wake-word background thread may listen.
        self.wake_enabled = threading.Event()
        self.wake_enabled.set()

        # Requests the detector to exit listenWakeWord().
        self.wake_pause_requested = threading.Event()

        # Confirms that the microphone has been released.
        self.wake_paused = threading.Event()
        self.wake_paused.set()

        # Set immediately when "Hey Echo" is detected.
        self.interrupt_pending = threading.Event()

        self.state_lock = threading.Lock()

        self.current_request_id = 0

        self.current_cancel_event: Optional[
            threading.Event
        ] = None

    def run(self) -> None:
        wake_thread = threading.Thread(
            target=self._wakeWordLoop,
            name="WakeWordThread",
            daemon=True,
        )

        wake_thread.start()

        print("[Controller] Study Buddy is ready.")

        try:
            while not self.shutdown_event.is_set():
                try:
                    event_type, request_id = (
                        self.events.get(timeout=0.2)
                    )
                except queue.Empty:
                    continue

                if event_type == WAKE_EVENT:
                    self._handleWakeWord()

                elif event_type == ANSWER_FINISHED_EVENT:
                    if request_id is not None:
                        self._handleAnswerFinished(
                            request_id
                        )

        except KeyboardInterrupt:
            print("\n[Controller] Stopping Study Buddy...")

        finally:
            self.close()

    def _wakeWordLoop(self) -> None:
        """
        Continuously listen for "Hey Echo" in the background.
        """

        while not self.shutdown_event.is_set():
            self.wake_enabled.wait()

            if self.shutdown_event.is_set():
                break

            self.wake_paused.clear()

            detected = False

            try:
                detected = (
                    self.wake_word_detector
                    .listenWakeWord(
                        stop_event=(
                            self.wake_pause_requested
                        )
                    )
                )

            except Exception as error:
                if not self.shutdown_event.is_set():
                    print(
                        "[WakeWord] Background detector "
                        f"error: {error}"
                    )

            finally:
                self.wake_word_detector.releaseMicrophone()
                self.wake_paused.set()

            if self.shutdown_event.is_set():
                break

            # The controller intentionally paused the detector
            # so STT can use the microphone.
            if self.wake_pause_requested.is_set():
                continue

            if detected:
                # Do not start listening again until the
                # new question has been recorded.
                self.wake_enabled.clear()

                self.interrupt_pending.set()

                # Cancel the current answer logically.
                self._signalCurrentCancellation()

                # Stop its spoken audio immediately.
                self.tts.stop()

                self.events.put(
                    (WAKE_EVENT, None)
                )

    def _pauseWakeListener(self) -> None:
        """
        Pause wake-word detection and release the microphone.
        """

        self.wake_enabled.clear()
        self.wake_pause_requested.set()

        if not self.wake_paused.wait(timeout=2.0):
            print(
                "[Controller] Warning: wake-word "
                "microphone did not pause in time."
            )

    def _resumeWakeListener(self) -> None:
        """
        Resume background wake-word detection.
        """

        if self.shutdown_event.is_set():
            return

        self.wake_pause_requested.clear()
        self.wake_paused.clear()
        self.wake_enabled.set()

    def _handleWakeWord(self) -> None:
        """
        Stop the old answer and record a new question.
        """

        self.interrupt_pending.clear()

        self._signalCurrentCancellation()
        self.tts.stop()

        print(
            "\n[Controller] Hey Echo detected. "
            "Listening for the new question..."
        )

        question = (
            self.speech_to_text
            .listenAndTranscribe()
            .strip()
        )

        if not question:
            print(
                "[Controller] No question was detected. "
                "Returning to wake-word mode."
            )

            self._resumeWakeListener()
            return

        print(f"[Student] {question}")

        normalized_question = self._normalizeText(
            question
        )

        if normalized_question in {
            "exit",
            "quit",
            "stop study buddy",
            "shut down",
            "shutdown",
        }:
            closing_message = (
                "Ending the Study Buddy session."
            )

            print(f"[Echo] {closing_message}")
            self.tts.speak(closing_message)

            self.shutdown_event.set()
            return

        self._startAnswerThread(question)

        # Listen for "Hey Echo" while the answer is generated
        # and spoken.
        self._resumeWakeListener()

    def _startAnswerThread(
        self,
        question: str,
    ) -> None:
        """
        Start one worker thread for one question.
        """

        with self.state_lock:
            self.current_request_id += 1
            request_id = self.current_request_id

            cancel_event = threading.Event()
            self.current_cancel_event = cancel_event

        worker = threading.Thread(
            target=self._answerQuestion,
            args=(
                request_id,
                question,
                cancel_event,
            ),
            name=f"QuestionThread-{request_id}",
            daemon=True,
        )

        worker.start()

    def _answerQuestion(
        self,
        request_id: int,
        question: str,
        cancel_event: threading.Event,
    ) -> None:
        """
        Generate and speak one answer.

        An interrupted result is discarded.
        """

        try:
            print(
                f"[Question {request_id}] "
                "Generating answer..."
            )

            # ==================== RAG CODE ====================
            # Enable this when your RAG dependencies,
            # Chroma database, Ollama model, and embeddings
            # are ready.
            #
            # response = self.assistant.answer(question)
            # ================== END RAG CODE ==================

            # ============== TEMPORARY TEST RESPONSE ==============
            # Delete this when the RAG call above is enabled.
            if self.assistant is None:
                response = (
                    "This is a temporary answer used to test "
                    "wake-word interruption. Echo should stop "
                    "speaking immediately when you say Hey Echo."
                )
            else:
                # ==================== RAG CALL ====================
                response = self.assistant.answer(question)
                # ================== END RAG CALL ==================
            # ============ END TEMPORARY TEST RESPONSE ============

            if not self._isCurrentRequest(
                request_id,
                cancel_event,
            ):
                print(
                    f"[Question {request_id}] "
                    "Interrupted result discarded."
                )
                return

            print(f"[Echo] {response}")

            completed = self.tts.speak(response)

            if not completed:
                print(
                    f"[Question {request_id}] "
                    "Speech interrupted."
                )
                return

            if not self._isCurrentRequest(
                request_id,
                cancel_event,
            ):
                return

            self.events.put(
                (
                    ANSWER_FINISHED_EVENT,
                    request_id,
                )
            )

        except Exception as error:
            if not cancel_event.is_set():
                print(
                    f"[Question {request_id}] "
                    f"Error: {error}"
                )

    def _handleAnswerFinished(
        self,
        request_id: int,
    ) -> None:
        """
        Ask for another question after a normal answer.
        """

        with self.state_lock:
            if request_id != self.current_request_id:
                return

            self.current_cancel_event = None

        if self.interrupt_pending.is_set():
            return

        follow_up_prompt = (
            "Do you have any more questions?"
        )

        print(f"[Echo] {follow_up_prompt}")

        prompt_completed = self.tts.speak(
            follow_up_prompt
        )

        # "Hey Echo" may have interrupted the prompt.
        if (
            not prompt_completed
            or self.interrupt_pending.is_set()
        ):
            return

        # The wake-word listener currently owns the microphone.
        # Pause it before Faster-Whisper starts.
        self._pauseWakeListener()

        # Handle a wake-word detection that occurred during the
        # small transition between TTS and microphone pausing.
        if self.interrupt_pending.is_set():
            return

        print(
            "[Controller] Waiting briefly for a "
            "follow-up question..."
        )

        follow_up = (
            self.speech_to_text
            .listenAndTranscribe(
                wait_for_speech_seconds=(
                    self.follow_up_wait_seconds
                )
            )
            .strip()
        )

        if not follow_up:
            print(
                "[Controller] No follow-up was detected. "
                "Returning to wake-word mode."
            )

            self._resumeWakeListener()
            return

        print(f"[Student] {follow_up}")

        normalized_follow_up = self._normalizeText(
            follow_up
        )

        if normalized_follow_up in {
            "no",
            "nope",
            "no thanks",
            "no thank you",
            "not now",
            "that is all",
            "that's all",
            "nothing else",
            "i am done",
            "i'm done",
        }:
            print(
                "[Controller] Conversation finished. "
                "Waiting for Hey Echo."
            )

            self._resumeWakeListener()
            return

        if normalized_follow_up in {
            "exit",
            "quit",
            "stop study buddy",
            "shut down",
            "shutdown",
        }:
            closing_message = (
                "Ending the Study Buddy session."
            )

            print(f"[Echo] {closing_message}")
            self.tts.speak(closing_message)

            self.shutdown_event.set()
            return

        # The student asked another question during the
        # allowed follow-up window.
        self._startAnswerThread(follow_up)
        self._resumeWakeListener()

    def _signalCurrentCancellation(self) -> None:
        with self.state_lock:
            if self.current_cancel_event is not None:
                self.current_cancel_event.set()

    def _isCurrentRequest(
        self,
        request_id: int,
        cancel_event: threading.Event,
    ) -> bool:
        with self.state_lock:
            return (
                request_id == self.current_request_id
                and not cancel_event.is_set()
            )

    @staticmethod
    def _normalizeText(text: str) -> str:
        normalized = text.lower().strip()

        normalized = normalized.translate(
            str.maketrans(
                "",
                "",
                ".,!?;:",
            )
        )

        return " ".join(normalized.split())

    def close(self) -> None:
        self.shutdown_event.set()

        self._signalCurrentCancellation()
        self.tts.stop()

        # Wake the background thread so it can terminate.
        self.wake_pause_requested.set()
        self.wake_enabled.set()

        self.wake_paused.wait(timeout=1.0)

        try:
            self.wake_word_detector.close()
        except Exception:
            pass