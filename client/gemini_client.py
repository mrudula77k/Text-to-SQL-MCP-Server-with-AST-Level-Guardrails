import os
import sys
import asyncio
from typing import List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types

async def main():
    # 1. Ensure Gemini API key is set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is missing.")
        sys.exit(1)

    # Initialize the new Google GenAI client
    client = genai.Client(api_key=api_key)

    # 2. Configure the MCP Stdio Connection
    # This spawns your server as a subprocess, just like the inspector did
    server_params = StdioServerParameters(
        command="python",
        args=["server/server.py"]
    )

    print("Starting MCP Server and connecting Gemini...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 3. Fetch available tools from the MCP server
            mcp_tools = await session.list_tools()
            
            # Convert MCP Tool schemas into Google GenAI FunctionDeclarations
            gemini_functions = []
            for tool in mcp_tools.tools:
                gemini_functions.append(
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.input_schema
                    )
                )
            
            # Bundle into a Tool object for the Gemini config
            gemini_tool = types.Tool(function_declarations=gemini_functions)

            # 4. Start the Gemini Chat Session
            chat = client.aio.chats.create(
                model="gemini-3.7-flash", # Or gemini-2.0-flash depending on your access
                config=types.GenerateContentConfig(
                    temperature=0, 
                    tools=[gemini_tool]
                )
            )

            print("\n✅ Connected! You can now ask questions about the database.")
            print("Type 'exit' or 'quit' to close.")

            # 5. The REPL Loop
            while True:
                # Use asyncio.to_thread so input() doesn't block the async event loop
                user_input = await asyncio.to_thread(input, "\nQuestion: ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue

                try:
                    # Send user question to Gemini
                    response = await chat.send_message(user_input)

                    # 6. Handle Tool Calling Loop
                    # Gemini might need to call multiple tools in sequence (e.g., list_tables -> get_table_schema -> run_query)
                    while response.function_calls:
                        function_responses: List[types.Part] = []
                        
                        for fc in response.function_calls:
                            print(f"  [Tool Called] -> {fc.name}({fc.args or {}})")
                            
                            try:
                                # Execute the requested tool on the MCP server
                                tool_result = await session.call_tool(fc.name, arguments=fc.args or {})
                                
                                # MCP returns a list of contents. Extract the text.
                                result_text = "\n".join(c.text for c in tool_result.content if c.type == 'text')
                                
                            except Exception as e:
                                result_text = f"Error executing tool: {str(e)}"
                            
                            # Package the result back into the format Gemini expects
                            function_responses.append(
                                types.Part.from_function_response(
                                    name=fc.name,
                                    response={"result": result_text}
                                )
                            )
                        
                        # Send the tool execution results back to Gemini so it can continue reasoning
                        response = await chat.send_message(function_responses)

                    # Print Gemini's final synthesized answer
                    print(f"\nAnswer: {response.text}")

                except Exception as e:
                    print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    # Suppress verbose logging from underlying libraries if desired
    asyncio.run(main())