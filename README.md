Fyyur
-----

## Introduction

Fyyur is a musical venue and artist booking site that facilitates the discovery and bookings of shows between local performing artists and venues. This site lets you list new artists and venues, discover them, and list shows with artists as a venue owner.

We want Fyyur to be the next new platform that artists and musical venues can use to find each other, and discover new music shows. Let's make that happen!

## Tech Stack (Dependencies)
If you are developing the app further, you will need to set up the developer environment.  For this, we use [pipenv](https://pipenv-fork.readthedocs.io/en/latest/).  You can find [instructions on how to set it up here](https://pipenv-fork.readthedocs.io/en/latest/install.html).  It is the preferred way to set up a python environment, replacing the use of a **requirements** file.

### 1. Backend Dependencies
Our tech stack will include the following:
 * **virtualenv** as a tool to create isolated Python environments
 * **SQLAlchemy ORM** to be our ORM library of choice
 * **PostgreSQL** as our database of choice
 * **Python3** and **Flask** as our server language and server framework
 * **Flask-Migrate** for creating and running schema migrations
You can download and install the dependencies mentioned above using `pipenv` as:
```
pipenv install && pipenv shell
```
If you also want the dev packages, simply add the `--dev` flag, like so
```
pipenv install --dev && pipenv shell
```

### 2. Frontend Dependencies
You must have the **HTML**, **CSS**, and **Javascript** with [Bootstrap 3](https://getbootstrap.com/docs/3.4/customize/) for our website's frontend. Bootstrap can only be installed by Node Package Manager (NPM). Therefore, if not already, download and install the [Node.js](https://nodejs.org/en/download/). Windows users must run the executable as an Administrator, and restart the computer after installation. After successfully installing the Node, verify the installation as shown below.
```
node -v
npm -v
```
Install [Bootstrap 3](https://getbootstrap.com/docs/3.3/getting-started/) for the website's frontend:
```
npm init -y
npm install bootstrap@3
```

Overall:
* Models are located in the [models.py](models.py) file.
* Controllers are located in `app.py`.
* The web frontend is located in `templates/`, which builds static assets deployed to the web server at `static/`.
* Web forms for creating data are located in `form.py`


Highlight folders/files:
* `templates/pages` -- Defines the pages that are rendered to the site. These templates render views based on data passed into the template’s view, in the controllers defined in `app.py`. These pages successfully represent the data to the user.
* `templates/layouts` -- Defines the layout that a page can be contained in to define footer and header code for a given page.
* `templates/forms` -- Defines the forms used to create new artists, shows, and venues.
* `app.py` -- Defines routes that match the user’s URL, and controllers which handle data and renders views to the user. This is the main file you will be working on to connect to and manipulate the database and render views with data to the user, based on the URL.
* `models.py` -- Defines the data models that set up the database tables.
* `config.py` -- Stores configuration variables and instructions, separate from the main application code. This is where you will need to connect to the database.  You can use an environment variable `DATABASE_URL` to define the connection.
* `.env` -- You need to define your own `.env` file and have the following variables defined:
```
FLASK_APP=app
FLASK_ENV=development
DATABASE_URL="postgresql://fyyurapp:fyyurpassword@localhost:5432/fyyur"
```
You can obviously replace the DATABASE_URL with your own.  This file should not be committed to github and has been added to the [.gitignore](.gitignore) file.
When you run `pipenv shell`, the `.env` file is automatically loaded into the environment.

### 3. Docker and Makefile
You can use docker to bring up a postgres service to use with this project.

Files for docker:
* `docker-compose.yml` -- Defines the postgres service that will work with the default connection specified in `config.py` under `SQLALCHEMY_DATABASE_URI` which is used when `DATABASE_URL` is not specified.
* `Makefile` -- Defines the instruction `make db` which you can use to bring up the postgres service with docker.  **Docker should be running when you run this command**

### 4. Seed data
If you wish to have some example records in the database, you have the following tools:

Files for seed data:
* `data.py` -- A collection of data points.  These can also be used for tests.
* `load_data.py` -- The instructions necessary to load the data from `data.py` into the database, including upgrading the database using `flask-migrate`

To load the seed data into the database, use:
```
python load_data.py
```
Your databse should be accessible for this to work.

## Development Setup
1. **Download the project starter code locally**
```
git clone https://github.com/aj-cloete/udacity-fyyur.git
cd udacity-fyyur
```

2. **Initialize and activate a pipenv using:**
```
pipenv install --dev
pipenv shell
```

4. **Install the dependencies:**
```
pip install -r requirements.txt
```

5. **Run the development server:**
```
export FLASK_APP=app # link to your app.py file
export FLASK_ENV=development # enables debug mode
flask run
```

6. **Verify on the Browser**<br>
Navigate to project homepage [http://127.0.0.1:5000/](http://127.0.0.1:5000/) or [http://localhost:5000](http://localhost:5000)
