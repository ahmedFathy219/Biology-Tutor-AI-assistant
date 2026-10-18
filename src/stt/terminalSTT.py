# src/stt/terminalSTT.py

class TerminalSTT:
    """
    Provides text input via the terminal as an alternative to speech-to-text.
    """
    def listenAndTranscribe(self, wait_for_speech_seconds: float = None) -> str:
        """
        Capture user input from the terminal.
        The wait_for_speech_seconds parameter is ignored in text mode.
        """
        try:
            # Using a clear prompt to indicate the system is waiting for user input
            text = input("\n[Terminal Input] >> ").strip()
            return text
        except EOFError:
            return ""
        except KeyboardInterrupt:
            # Return empty string to allow main loop to handle exit or continue
            return ""
