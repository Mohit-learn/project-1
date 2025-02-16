from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import os
from dotenv import load_dotenv
import httpx
import subprocess ,sys
from pydantic import BaseModel
load_dotenv()
AIPROXY_TOKEN = os.getenv("AIPROXY_TOKEN")

app = FastAPI()
class TaskRequest(BaseModel):
    task: str
DATA_DIR = os.path.dirname(os.path.abspath(__file__))  # Ensuring all operations stay within /data

def query_gpt(user_input):
    system_input='''You are an AI agent that converts task descriptions into executable Python scripts.  
Your job is to generate a fully functional Python script based on the given task.  

Guidelines:  
1. **Generate a complete and functional Python script** that performs the requested task.  
2. **Break down the task into structured steps before writing code** (e.g., read input, process data, write output).  
3. **Ensure the script correctly reads input from specified files and writes the correct output.**  
4. **Handle errors gracefully** (e.g., missing files, invalid data, external dependencies).  
5. **Use only standard Python libraries unless explicitly required otherwise.**  
6. **If external tools are needed (e.g., uv, prettier, SQLite), check if they are installed before using them.**  
7. **Ensure all scripts are written in Python 3 and formatted properly.**  
8. **Do not provide explanations—only output the complete Python script.**  
9. **Tasks can be given in any language, but the script should always be written in English.**  
10. **If the task requires an email, use this default email: `"21f3002378@ds.study.iitm.ac.in"`**  
11. **If downloading files from a URL, validate the download and handle network failures properly.**  
12. **Include logging/debugging statements to assist in troubleshooting errors.** 
Example Input:  
"Count the number of Wednesdays in /data/dates.txt and write the count to /data/dates-wednesdays.txt"  

Example Output:  
```python
import datetime

input_file = "/data/dates.txt"
output_file = "/data/dates-wednesdays.txt"

try:
    with open(input_file, "r", encoding="utf-8") as file:
        dates = file.readlines()

    count = sum(1 for date in dates if datetime.datetime.strptime(date.strip(), "%Y-%m-d").weekday() == 2)

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(str(count))

except Exception as e:
    print(f"Error processing file: e")
'''
  
    response = httpx.post(
        "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('AIPROXY_TOKEN')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system_input},{"role": "user", "content": user_input}],
        },
    )
    gpt_response = response.json()["choices"][0]["message"]["content"]
    
    # Remove markdown code block markers if present
    if gpt_response.startswith("```python"):
        gpt_response = gpt_response.strip("```python").strip("```").strip()
    
    return gpt_response  # Return the cleaned Python code

def save_script(script_code: str, filename: str = "generated_script.py") -> str:
    """Saves the script to a file and returns the file path."""
    script_path = os.path.join(DATA_DIR, filename)
    with open(script_path, "w", encoding="utf-8") as script_file:
        script_file.write(script_code)
    return script_path

#def execute_script(script_path: str) -> str:
    #"""Runs the saved script using subprocess and returns the output."""
    #try:
        #result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, check=True)
        #return result.stdout.strip()
    #except subprocess.CalledProcessError as e:
        #raise HTTPException(status_code=500, detail={"error": "Script execution failed", "details": e.stderr})
def execute_script(script_path: str) -> str:
    """Runs the saved script using subprocess and returns the output or raises an error."""
    try:
        result = subprocess.run(
            [sys.executable, script_path], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else "Unknown error"
        raise HTTPException(status_code=500, detail={"error": "Script execution failed", "details": error_message})

@app.get("/read")
async def read_file(path: str):
    """
    Reads the content of a file from the `/data` directory.
    Returns a 200 response if successful.
    Returns a 404 response if the file does not exist.
    """
    file_path = os.path.join(DATA_DIR, "data", path)


    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    return PlainTextResponse(content, status_code=200)

@app.post("/run")
def run_task(request: TaskRequest):
    """Handles API request, queries LLM, saves, executes script, and returns output."""
    if not request.task:
        raise HTTPException(status_code=400, detail="Task description is required")

    try:
        
        script_code = query_gpt(request.task)  # Get generated script from LLM
        
        script_path = save_script(script_code)  # Save script to file
        
        output = execute_script(script_path)  # Execute the script
        

        return JSONResponse(content={"message": "Task executed successfully", "output": output}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
