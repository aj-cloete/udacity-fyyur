# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import logging
from datetime import datetime
from logging import FileHandler, Formatter

import babel
import dateutil.parser
import sqlalchemy as sa
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_migrate import Migrate, MigrateCommand
from flask_moment import Moment
from flask_script import Manager

from forms import ArtistForm, ShowForm, VenueForm
from models import Artist, Show, Venue, db

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")

# Database initialisation
db.init_app(app)

# Migrations
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command("db", MigrateCommand)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


def _get_shows(when="upcoming", groupby="venue"):
    """Get the [when = "upcoming"/"past"] shows from database as subquery"""
    now = datetime.now()
    if when.lower() in ("upcoming", "future"):
        when_filter = Show.start_time > now
    else:
        when_filter = Show.start_time <= now
    upcoming_show = (
        Show.query.with_entities(
            Show.venue_id if "venue" in groupby else Show.artist_id,
            sa.func.coalesce(sa.func.sum(1).filter(when_filter), 0).label(
                f"{when}_show"
            ),
        )
        .group_by(Show.venue_id if "venue" in groupby else Show.artist_id)
        .subquery()
    )
    return upcoming_show


def _as_dict(instance):
    """Get the db.Model instance as a python dict"""
    instance_dict = instance.__dict__
    return {k: instance_dict[k] for k in instance_dict if k[0] != "_"}


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    upcoming = _get_shows("upcoming")
    city = Venue.query.with_entities(Venue.city, Venue.state).group_by("city", "state")
    venue = Venue.query.join(upcoming, isouter=True).with_entities(
        Venue.city, Venue.state, Venue.id, Venue.name, upcoming.c.upcoming_show
    )
    data = [
        {
            "city": c.city,
            "state": c.state,
            "venues": [
                {"id": v.id, "name": v.name, "num_upcoming_shows": v.upcoming_show}
                for v in venue.filter(
                    sa.and_(Venue.state == c.state, Venue.city == c.city)
                )
            ],
        }
        for c in city
    ]
    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    upcoming = _get_shows("upcoming")
    search_term = request.form.get("search_term", "")
    search = (
        Venue.query.join(upcoming, isouter=True)
        .with_entities(
            Venue.id,
            Venue.name,
            sa.func.coalesce(upcoming.c.upcoming_show, 0).label("upcoming_shows"),
        )
        .filter(Venue.name.ilike(f"%{search_term}%"))
        .all()
    )
    response = {
        "count": len(search),
        "data": [
            {"id": sr.id, "name": sr.name, "num_upcoming_shows": sr.upcoming_shows}
            for sr in search
        ],
    }
    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    # TODO: fix genres - should be list
    upcoming = _get_shows("upcoming")
    past = _get_shows("past")
    venue, num_upcoming, num_past = (
        Venue.query.filter(Venue.id == venue_id)
        .join(upcoming, isouter=True)
        .join(past, isouter=True)
        .add_column(upcoming.c.upcoming_show.label("upcoming_shows_count"))
        .add_column(past.c.past_show.label("past_shows_count"))
        .first()
    )

    data = _as_dict(venue)
    data["genres"] = (
        venue.genres.replace("{", "").replace("}", "").replace('"', "").split(",")
    )
    data.update(
        {
            "upcoming_shows_count": num_upcoming if num_upcoming else 0,
            "past_shows_count": num_past if num_past else 0,
            "upcoming_shows": [
                {
                    "artist_id": s.artist_id,
                    "artist_name": s.name,
                    "artist_image_link": s.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in Show.query.with_entities(
                    Show.artist_id, Artist.name, Artist.image_link, Show.start_time
                )
                .filter(Show.venue_id == venue_id, Show.start_time > datetime.now())
                .join(Artist, isouter=True)
                .all()
            ],
            "past_shows": [
                {
                    "artist_id": s.artist_id,
                    "artist_name": s.name,
                    "artist_image_link": s.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in Show.query.with_entities(
                    Show.artist_id, Artist.name, Artist.image_link, Show.start_time
                )
                .filter(Show.venue_id == venue_id, Show.start_time <= datetime.now())
                .join(Artist, isouter=True)
                .all()
            ],
        }
    )
    return render_template("pages/show_venue.html", venue=data)


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    form = VenueForm()
    venue = Venue()
    form.populate_obj(venue)
    venue.id = Venue.query.with_entities(sa.func.max(Venue.id)).first()[0] + 1
    try:
        db.session.add(venue)
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully listed!")
    except Exception as e:
        app.logger.info(e)
        flash(
            f'An error occurred. Venue {request.form["name"]} could not be listed.',
            "error",
        )
    return render_template("pages/home.html", form=form, data=venue)


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    try:
        db.session.delete(venue)
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully deleted!")
    except Exception as e:
        app.logger.info(e)
        flash(
            f'An error occurred. Venue {request.form["name"]} could not be deleted.',
            "error",
        )

    # TODO: BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return None


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    data = [
        {
            "id": a.id,
            "name": a.name,
        }
        for a in Artist.query.all()
    ]
    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form.get("search_term", "")
    result = Artist.query.filter(Artist.name.ilike(f"%{search_term}%"))
    response = {
        "count": result.count(),
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "num_upcoming_shows": Show.query.filter(Show.artist_id == r.id)
                .filter(Show.start_time > datetime.now())
                .count(),
            }
            for r in result.all()
        ],
    }
    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    # shows the venue page with the given venue_id
    # TODO: replace with real venue data from the venues table, using venue_id
    artist = Artist.query.get(artist_id)
    data = _as_dict(artist)
    # TODO: fix genres - should be a list.
    data["genres"] = (
        artist.genres.replace("{", "").replace("}", "").replace('"', "").split(",")
    )
    app.logger.info(data)
    #
    # data1 = {
    # .     "id": 4,
    # .    "name": "Guns N Petals",
    #  .   "genres": ["Rock n Roll"],
    #   .  "city": "San Francisco",
    #    . "state": "CA",
    #     ."phone": "326-123-5000",
    # x     "website": "https://www.gunsnpetalsband.com",
    # .    "facebook_link": "https://www.facebook.com/GunsNPetals",
    #  .   "seeking_venue": True,
    #   x  "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    #    . "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    # x    "past_shows": [
    #         {
    #             "venue_id": 1,
    #             "venue_name": "The Musical Hop",
    #             "venue_image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    #             "start_time": "2019-05-21T21:30:00.000Z",
    #         }
    #     ],
    #  x   "upcoming_shows": [],
    #  x   "past_shows_count": 1,
    #  x   "upcoming_shows_count": 0,
    # }
    # data2 = {
    #     "id": 5,
    #     "name": "Matt Quevedo",
    #     "genres": ["Jazz"],
    #     "city": "New York",
    #     "state": "NY",
    #     "phone": "300-400-5000",
    #     "facebook_link": "https://www.facebook.com/mattquevedo923251523",
    #     "seeking_venue": False,
    #     "image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
    #     "past_shows": [
    #         {
    #             "venue_id": 3,
    #             "venue_name": "Park Square Live Music & Coffee",
    #             "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    #             "start_time": "2019-06-15T23:00:00.000Z",
    #         }
    #     ],
    #     "upcoming_shows": [],
    #     "past_shows_count": 1,
    #     "upcoming_shows_count": 0,
    # }
    # data3 = {
    #     "id": 6,
    #     "name": "The Wild Sax Band",
    #     "genres": ["Jazz", "Classical"],
    #     "city": "San Francisco",
    #     "state": "CA",
    #     "phone": "432-325-5432",
    #     "seeking_venue": False,
    #     "image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
    #     "past_shows": [],
    #     "upcoming_shows": [
    #         {
    #             "venue_id": 3,
    #             "venue_name": "Park Square Live Music & Coffee",
    #             "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    #             "start_time": "2035-04-01T20:00:00.000Z",
    #         },
    #         {
    #             "venue_id": 3,
    #             "venue_name": "Park Square Live Music & Coffee",
    #             "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    #             "start_time": "2035-04-08T20:00:00.000Z",
    #         },
    #         {
    #             "venue_id": 3,
    #             "venue_name": "Park Square Live Music & Coffee",
    #             "venue_image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    #             "start_time": "2035-04-15T20:00:00.000Z",
    #         },
    #     ],
    #     "past_shows_count": 0,
    #     "upcoming_shows_count": 3,
    # }
    # data = list(filter(lambda d: d["id"] == artist_id, [data1, data2, data3]))[0]
    return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    # artist = {
    #     "id": 4,
    #     "name": "Guns N Petals",
    #     "genres": ["Rock n Roll"],
    #     "city": "San Francisco",
    #     "state": "CA",
    #     "phone": "326-123-5000",
    #     "website": "https://www.gunsnpetalsband.com",
    #     "facebook_link": "https://www.facebook.com/GunsNPetals",
    #     "seeking_venue": True,
    #     "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    #     "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    # }
    # TODO: populate form with fields from artist with ID <artist_id>
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    form = VenueForm()
    venue = {
        "id": 1,
        "name": "The Musical Hop",
        "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
        "address": "1015 Folsom Street",
        "city": "San Francisco",
        "state": "CA",
        "phone": "123-123-1234",
        "website": "https://www.themusicalhop.com",
        "facebook_link": "https://www.facebook.com/TheMusicalHop",
        "seeking_talent": True,
        "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
        "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    }
    # TODO: populate form with values from venue with ID <venue_id>
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    # called upon submitting the new artist listing form
    # TODO: insert form data as a new Venue record in the db, instead
    # TODO: modify data to be the data object returned from db insertion

    # on successful db insert, flash success
    flash("Artist " + request.form["name"] + " was successfully listed!")
    # TODO: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
    return render_template("pages/home.html")


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    #       num_shows should be aggregated based on number of upcoming shows per venue.
    data = [
        {
            "venue_id": 1,
            "venue_name": "The Musical Hop",
            "artist_id": 4,
            "artist_name": "Guns N Petals",
            "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
            "start_time": "2019-05-21T21:30:00.000Z",
        },
        {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "artist_id": 5,
            "artist_name": "Matt Quevedo",
            "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
            "start_time": "2019-06-15T23:00:00.000Z",
        },
        {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "artist_id": 6,
            "artist_name": "The Wild Sax Band",
            "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
            "start_time": "2035-04-01T20:00:00.000Z",
        },
        {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "artist_id": 6,
            "artist_name": "The Wild Sax Band",
            "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
            "start_time": "2035-04-08T20:00:00.000Z",
        },
        {
            "venue_id": 3,
            "venue_name": "Park Square Live Music & Coffee",
            "artist_id": 6,
            "artist_name": "The Wild Sax Band",
            "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
            "start_time": "2035-04-15T20:00:00.000Z",
        },
    ]
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    # TODO: insert form data as a new Show record in the db, instead

    # on successful db insert, flash success
    flash("Show was successfully listed!")
    # TODO: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Show could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    manager.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
