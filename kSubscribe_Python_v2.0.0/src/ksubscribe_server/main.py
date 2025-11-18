import os
import sys
import uvicorn

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

class main:
    
    def main():
   
        return
    

if __name__ == "__main__":
    main()
    # uvicorn.run("fastApi.fastApi:app", host="127.0.0.1", port=8000)
    uvicorn.run("fastApi.fastApi:app", host="10.100.12.70", port=7000) 
    
    