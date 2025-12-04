from main import run_agent

def test_agent():
    print("Starting agent test (Native SDK)...")
    query = "Who is the CEO of Google?"
    print(f"Query: {query}")
    
    try:
        response = run_agent(query)
        print("Agent execution completed.")
        
        print(f"Response Text: {response.text}")
        
        if response.candidates and response.candidates[0].grounding_metadata:
            print("Grounding metadata found.")
            metadata = response.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                print(f"Found {len(metadata.grounding_chunks)} grounding chunks.")
        else:
            print("No grounding metadata found (this might be expected if the model didn't use search).")

    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_agent()
