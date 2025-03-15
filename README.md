<h1>To run on the Project on Mac:</h1>
 <h2>Enter the following in your terminal in the github folder <br>
   python3 -m venv path/to/venv <br>
   source path/to/venv/bin/activate <br>
   python webscraping.py <br> </h2>

<h1>To run the Project on Window:</h1>
<h2>Enter the following in your terminal in the github folder <br>
    python -m venv venv <br>
    venv\Scripts\activate <br>
    python webscraping.py <br> </h2>

<h1>How to run project using Docker</h1>
    <h2> Make sure docker desktop is running on your computer. <br>
    The first time do the docker build and run commands. <br>
    Any other times after that only do docker start command.<br>
    Enter the following in your terminal <br>
    docker build --no-cache -t my-flask-app . <br>
    docker run -it  my-flask-app <br>
    ############################################<br>
    docker start "container_id_or_name" <br>
    logs will be in docker in no in your local terminal<br>
    If you add any other packages/imports to the project please put them in requirements.txt

    
