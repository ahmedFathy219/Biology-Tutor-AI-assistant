from wake_word import getWakeWordDetector
from rag import BioAssistant
from dotenv import load_dotenv
import time

load_dotenv()

assistant = BioAssistant()

detector = getWakeWordDetector()
while(True):
    detector.listenWakeWord()
    print("Wake word detected! Listening for command...")

    #placeholder for STT

    #for testing, take text input
    transcription = input("Type your question (or 'exit' to stop): ")

    if(transcription.lower() == "exit"):
        break

    #querry the assistant    
    response = assistant.answer(transcription)


    #for testing output, output to console 
    print(f"Echo: {response}")


    #placeholder for TTS    
    
    # wait 5 seconds to prevent multiple detections of wakeword
    time.sleep(5)