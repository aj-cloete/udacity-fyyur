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

from forms import ArtistForm, NewArtistForm, NewShowForm, VenueForm
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


def _as_dict(instance):
    """Get the db.Model instance as a python dict"""
    try:
        instance_dict = instance.__dict__
    except AttributeError:
        return None
    return {k: instance_dict[k] for k in instance_dict if k[0] != "_"}


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    data = [
        {
            "city": cs.city,
            "state": cs.state,
            "venues": [
                {
                    "id": v.id,
                    "name": v.name,
                    "num_upcoming_shows": Show.query.filter(
                        Show.venue_id == v.id, Show.start_time > datetime.now()
                    ).count(),
                }
                for v in Venue.query.filter(
                    Venue.city == cs.city, Venue.state == cs.state
                ).all()
            ],
        }
        for cs in Venue.query.with_entities(Venue.city, Venue.state)
        .group_by("city", "state")
        .all()
    ]
    return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
    search_term = request.form.get("search_term", "")
    search = Venue.query.filter(Venue.name.ilike(f"%{search_term}%"))
    response = {
        "count": search.count(),
        "data": [
            dict(
                id=sr.id,
                name=sr.name,
                num_upcoming_shows=Show.query.filter(
                    Show.venue_id == sr.id, Show.start_time > datetime.now()
                ).count(),
            )
            for sr in search.all()
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
    venue = Venue.query.get(venue_id)
    if venue is None:
        return not_found_error(f"Venue with id {venue_id} not found")

    data = _as_dict(venue)
    data["genres"] = (
        venue.genres.replace("{", "").replace("}", "").replace('"', "").split(",")
    )
    venue_shows = Show.query.filter_by(venue_id=venue.id)
    prev_shows = venue_shows.filter(Show.start_time <= datetime.now())
    next_shows = venue_shows.filter(Show.start_time > datetime.now())
    data.update(
        {
            "upcoming_shows_count": next_shows.count(),
            "upcoming_shows": [
                {
                    "artist_id": s.artist.id,
                    "artist_name": s.artist.name,
                    "artist_image_link": s.artist.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in next_shows.join(Artist, isouter=True).all()
            ],
            "past_shows_count": prev_shows.count(),
            "past_shows": [
                {
                    "artist_id": s.artist.id,
                    "artist_name": s.artist.name,
                    "artist_image_link": s.artist.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in prev_shows.join(Venue, isouter=True).all()
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
        db.session.rollback()
        app.logger.info(e)
        flash(
            f'An error occurred. Venue {request.form["name"]} could not be listed.',
            "error",
        )
    return render_template("pages/home.html", form=form, data=venue)


@app.route("/venues/<venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if venue is None:
        return not_found_error(f"Venue with id {venue_id} not found")
    try:
        db.session.delete(venue)
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully deleted!")
    except Exception as e:
        db.session.rollback()
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
    artist = Artist.query.get(artist_id)
    if artist is None:
        return not_found_error(f"Artist with id {artist_id} not found")
    data = _as_dict(artist)
    # TODO: fix genres - should be a list.
    data["genres"] = (
        artist.genres.replace("{", "").replace("}", "").replace('"', "").split(",")
    )
    artist_shows = Show.query.filter_by(artist_id=artist.id)
    prev_shows = artist_shows.filter(Show.start_time <= datetime.now())
    next_shows = artist_shows.filter(Show.start_time > datetime.now())
    data.update(
        {
            "upcoming_shows_count": next_shows.count(),
            "upcoming_shows": [
                {
                    "venue_id": s.venue_id,
                    "venue_name": s.venue.name,
                    "venue_image_link": s.venue.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in next_shows.join(Venue, isouter=True).all()
            ],
            "past_shows_count": prev_shows.count(),
            "past_shows": [
                {
                    "venue_id": s.venue_id,
                    "venue_name": s.venue.name,
                    "venue_image_link": s.venue.image_link,
                    "start_time": s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                }
                for s in prev_shows.join(Venue, isouter=True).all()
            ],
        }
    )
    return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if artist is None:
        return not_found_error(f"Artist with id {artist_id} not found")
    form = ArtistForm(obj=artist)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)
    if artist is None:
        return not_found_error(f"Artist with id {artist_id} not found")
    form = ArtistForm(data=_as_dict(artist))
    form.populate_obj(artist)
    try:
        db.session.add(artist)
        db.session.commit()
        flash("Artist " + request.form["name"] + " was successfully edited!")
    except Exception as e:
        db.session.rollback()
        app.logger.info(e)
        flash(
            f'An error occurred. Edited artist {request.form["name"]} could not be saved.',
            "error",
        )
    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if venue is None:
        return not_found_error(f"Venue with id {venue_id} not found")
    form = VenueForm(obj=venue)
    return render_template("forms/edit_venue.html", form=form, venue=venue)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    if venue is None:
        return not_found_error(f"Venue with id {venue_id} not found")
    form = VenueForm(data=_as_dict(venue))
    form.populate_obj(venue)
    try:
        db.session.add(venue)
        db.session.commit()
        flash("Venue " + request.form["name"] + " was successfully edited!")
    except Exception as e:
        db.session.rollback()
        app.logger.info(e)
        flash(
            f'An error occurred. Edited venue {request.form["name"]} could not be saved.',
            "error",
        )
    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = NewArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    # called upon submitting the new artist listing form
    form = NewArtistForm()
    artist = Artist()
    form.populate_obj(artist)
    try:
        db.session.add(artist)
        db.session.commit()
        # on successful db insert, flash success
        flash("Artist was successfully listed!")
    except Exception as e:
        app.logger.warn(e)
        flash("Artist was not successfully listed!", "error")
        db.session.rollback()
    return render_template("pages/home.html")


#  Delete Artist
#  ----------------------------------------------------------------


@app.route("/artists/<artist_id>", methods=["DELETE"])
def delete_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if artist is None:
        return not_found_error(f"Artist with id {artist_id} not found")
    try:
        db.session.delete(artist)
        db.session.commit()
        flash("Artist " + request.form["name"] + " was successfully deleted!")
    except Exception as e:
        db.session.rollback()
        app.logger.info(e)
        flash(
            f'An error occurred. Artist {request.form["name"]} could not be deleted.',
            "error",
        )


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    # displays list of shows at /shows
    data = [
        dict(
            venue_id=s.venue_id,
            venue_name=s.venue.name,
            artist_id=s.artist_id,
            artist_name=s.artist.name,
            artist_image_link=s.artist.image_link,
            start_time=s.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
        )
        for s in Show.query.all()
    ]
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = NewShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    form = NewShowForm()
    show = Show()
    form.populate_obj(show)
    try:
        db.session.add(show)
        db.session.commit()
        # on successful db insert, flash success
        flash("Show was successfully listed!")
    except Exception as e:
        app.logger.warn(e)
        flash("Show was not successfully listed!", "error")
        db.session.rollback()
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
