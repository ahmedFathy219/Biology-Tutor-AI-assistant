#!/usr/bin/env python3
"""
Test script for ST7735 display with auto-scroll and pagination
"""

import sys
import time
from pathlib import Path

# Add display directory to path
display_dir = Path(__file__).parent.parent / 'src' / 'display'
sys.path.insert(0, str(display_dir))

from st7735_display import TftDisplay

def test_landscape_mode():
    """Test landscape orientation"""
    print("\n=== Test: Landscape Mode ===")
    display = TftDisplay(dc_pin=24, reset_pin=25)
    
    if not display.start():
        print("Failed to start display")
        return None
    
    # Show a simple screen to verify orientation
    display.showWakeGuide()
    print("Landscape wake guide displayed")
    time.sleep(3)
    
    return display

def test_topic_scrolling(display):
    """Test auto-scrolling topics"""
    print("\n=== Test: Topic Scrolling ===")
    
    # Create many topics to test scrolling
    topics = [
        "Biology", "Chemistry", "Physics", "Astronomy",
        "Geology", "Ecology", "Genetics", "Robotics",
        "AI", "Mathematics", "History", "Geography"
    ]
    
    print("Showing scrolling topics...")
    display.showQuizTopics(topics)
    print(f"Topics will scroll every 1 second (default scroll rate)")
    time.sleep(10)  # Watch scrolling for 10 seconds
    
    print("✓ Topic scrolling test complete")

def test_text_pagination(display):
    """Test text pagination"""
    print("\n=== Test: Text Pagination ===")
    
    # Long text that needs pagination
    long_question = (
        "Explain the process of photosynthesis including the role of "
        "chlorophyll in capturing sunlight, the importance of water and "
        "carbon dioxide as raw materials, and how glucose and oxygen are "
        "produced as final products. Also describe how this process is "
        "essential for maintaining life on Earth."
    )
    
    print("Showing paginated question...")
    display.showQuizQuestion(1, "Biology", long_question)
    print(f"Question will paginate every 3 seconds (default page rate)")
    time.sleep(12)  # Watch pagination for 12 seconds
    
    print("✓ Text pagination test complete")

def test_custom_rates():
    """Test custom scroll and page rates"""
    print("\n=== Test: Custom Rates ===")
    
    # Create display with custom rates
    display = TftDisplay(
        dc_pin=24, 
        reset_pin=25,
        scroll_rate=0.5,  # Fast scrolling (0.5 seconds)
        page_rate=1.5      # Fast pagination (1.5 seconds)
    )
    
    if not display.start():
        print("Failed to start display with custom rates")
        return None
    
    # Test fast scrolling
    topics = ["Topic1", "Topic2", "Topic3", "Topic4", 
              "Topic5", "Topic6", "Topic7", "Topic8"]
    
    print("Testing fast scrolling (0.5s rate)...")
    display.showQuizTopics(topics)
    time.sleep(5)
    
    # Test fast pagination
    long_text = (
        "This is a long message that will be split into multiple pages. "
        "Each page will display for only 1.5 seconds before moving to the "
        "next page. This tests the configurable pagination rate feature."
    )
    
    print("Testing fast pagination (1.5s rate)...")
    display.showQuizMessage(long_text, streakValue=2)
    time.sleep(6)
    
    display.close()
    print("✓ Custom rates test complete")
    return display

def test_looping():
    """Test that scrolling and pagination loop back"""
    print("\n=== Test: Looping Behavior ===")
    
    display = TftDisplay(dc_pin=24, reset_pin=25)
    
    if not display.start():
        print("Failed to start display")
        return
    
    # Test topic loop
    topics = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    print("Testing topic loop (should return to start)...")
    display.showQuizTopics(topics)
    time.sleep(8)  # Watch full loop
    
    # Test page loop
    long_text = (
        "Page one content goes here with enough text to wrap. "
        "Page two content follows after the first page. "
        "Page three content continues the explanation. "
        "Page four content should loop back to page one."
    )
    
    print("Testing page loop (should return to first page)...")
    display.showFlashcardAnswer("Test", long_text)
    time.sleep(10)  # Watch full loop
    
    display.close()
    print("✓ Looping test complete")

def main():
    """Main test function"""
    print("=" * 50)
    print("ST7735 Display - Auto-scroll & Pagination Test")
    print("=" * 50)
    
    # Test landscape mode
    display = test_landscape_mode()
    if not display:
        return
    
    # Test scrolling
    test_topic_scrolling(display)
    
    # Test pagination
    test_text_pagination(display)
    
    # Clean up
    display.close()
    
    # Test custom rates
    test_custom_rates()
    
    # Test looping
    test_looping()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()