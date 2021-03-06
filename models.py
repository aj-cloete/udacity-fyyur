# ----------------------------------------------------------------------------#
# Models.
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    genres = db.Column(db.String(500))
    address = db.Column(db.String(120))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.BOOLEAN)
    seeking_description = db.Column(db.String(500))
    image_link = db.Column(db.String(500))

    shows = db.relationship("Show", backref="venue")


class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(500))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    website = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.BOOLEAN)
    seeking_description = db.Column(db.String(500))
    image_link = db.Column(db.String(500))

    shows = db.relationship("Show", backref="artist")


class Show(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venue_id = db.Column(db.Integer, db.ForeignKey("venue.id"), nullable=True)
    artist_id = db.Column(db.Integer, db.ForeignKey("artist.id"), nullable=True)
    start_time = db.Column(db.TIMESTAMP)
    __table_args__ = (
        db.UniqueConstraint(
            "venue_id", "artist_id", "start_time", name="uniq_venue_artist_time"
        ),
    )
