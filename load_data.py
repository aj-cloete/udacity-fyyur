import os

from app import Artist, Show, Venue, app, db
from data import (
    show_artist_data1,
    show_artist_data2,
    show_artist_data3,
    show_venue_data1,
    show_venue_data2,
    show_venue_data3,
    shows_data,
)

# Run migration
os.system("flask db upgrade")

# Set up app context for inserting data
ctx = app.app_context()
ctx.push()

app.logger.info("Loading data into database")

vkeys = [
    "id",
    "name",
    "genres",
    "address",
    "city",
    "state",
    "phone",
    "website",
    "facebook_link",
    "seeking_talent",
    "seeking_description",
    "image_link",
]

v1 = Venue(**{k: show_venue_data1[k] for k in vkeys if k in show_venue_data1})
v2 = Venue(**{k: show_venue_data2[k] for k in vkeys if k in show_venue_data2})
v3 = Venue(**{k: show_venue_data3[k] for k in vkeys if k in show_venue_data3})
db.session.add_all([v1, v2, v3])
# db.session.commit()

akeys = [
    "id",
    "name",
    "genres",
    "city",
    "state",
    "phone",
    "seeking_venue",
    "seeking_description",
    "website",
    "image_link",
    "facebook_link",
]
a1 = Artist(**{k: show_artist_data1[k] for k in akeys if k in show_artist_data1})
a2 = Artist(**{k: show_artist_data2[k] for k in akeys if k in show_artist_data2})
a3 = Artist(**{k: show_artist_data3[k] for k in akeys if k in show_artist_data3})
db.session.add_all([a1, a2, a3])

shows = []
skeys = ["venue_id", "artist_id", "start_time"]
for s in shows_data:
    shows.append(Show(**{k: s[k] for k in skeys if k in s}))
db.session.add_all(shows)
try:
    db.session.commit()
    app.logger.info("Data successfully loaded into database!")
except Exception as e:
    db.session.rollback()
    app.logger.error(f"Error loading data into database!\n{e}")

ctx.pop()
