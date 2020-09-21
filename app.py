#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import sys
import logging

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


logger = logging.getLogger('werkzeug') # grabs underlying WSGI logger
handler = logging.FileHandler('error.log') # creates handler for the log file
logger.addHandler(handler) # adds handler to the werkzeug WSGI logger
#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
Shows = db.Table("Shows",
                 db.Column("id", db.Integer, primary_key=True),
                 db.Column("artist_id", db.Integer, db.ForeignKey("Artist.id")),
                 db.Column("venue_id", db.Integer, db.ForeignKey("Venue.id")),
                 db.Column("start_time", db.DateTime, default=datetime.utcnow()))

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()))
    seeking_talent = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.String())
    website_link = db.Column(db.String(500))
    artists = db.relationship("Artist", secondary=Shows,
                              backref=db.backref('Venue',
                                            cascade="all,delete"), lazy=True)
class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean(), default=False)
    seeking_description = db.Column(db.String(300))
    website_link = db.Column(db.String(500))
    venues = db.relationship("Venue", secondary=Shows,  backref="Artist", lazy=True)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale="en")

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
  data = []

  areas = Venue.query \
      .with_entities(Venue.city, Venue.state) \
      .group_by(Venue.city, Venue.state) \
      .all()

  for area in areas:
    venues_data = []

    venues = Venue.query \
        .filter_by(state=area.state) \
        .filter_by(city=area.city) \
        .all()

    for venue in venues:
      upcoming_shows = Venue.query.join(Shows)\
                    .filter(Shows.c.start_time > datetime.now())\
                    .filter(Shows.c.venue_id == venue.id)\
                    .all()

      venues_data.append({
          'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': len(upcoming_shows)
      })

    data.append({
        'city': area.city,
        'state': area.state,
        'venues': venues_data
    })

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.ilike(f"%{search_term}%")).all()
  data = []

  for venue in venues:
    upcoming_shows = Venue.query \
        .join(Shows) \
        .filter(Shows.c.venue_id == venue.id) \
        .filter(Shows.c.start_time > datetime.now()) \
        .all()
    data.append({
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': len(upcoming_shows)
    })

  response = {
    'data': data,
    'count': len(venues)
  }      

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  venue = Venue.query.filter_by(id=venue_id).first()
  shows = db.session.query(Shows).filter(Shows.c.venue_id == venue.id).all()
  upcoming_shows = []
  past_shows = []
  
  for show in shows:
    artist = Artist.query.filter_by(id=show.artist_id).first()
    if(show.start_time >= datetime.now()):
      upcoming_shows.append({
        'artist_id': artist.id,
        'artist_name': artist.name,
        'artist_image_link': artist.image_link,
        'start_time': format_datetime(str(show.start_time)),
      })
    else:
      past_shows.append({
          'artist_id': artist.id,
          'artist_name': artist.name,
          'artist_image_link': artist.image_link,
          'start_time': format_datetime(str(show.start_time)),
      })

  #append upcoming shows    
  venue.upcoming_shows  = upcoming_shows
  venue.upcoming_shows_count = len(upcoming_shows) 

  #append past shows    
  venue.past_shows = past_shows
  venue.past_shows_count = len(past_shows) 

  return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  name = request.form['name']
  city = request.form['city']
  state = request.form['state']
  address = request.form['address']
  phone = request.form['phone']
  genres = request.form.getlist('genres')
  image_link = request.form['image_link']
  facebook_link = request.form['facebook_link']
  website_link = request.form['website_link']
  seeking_talent = True if 'seeking_talent' in request.form else False
  seeking_description = request.form['seeking_description']

  try:
    venue = Venue(
      name=name,
      city=city,
      state=state,
      address=address,
      phone=phone,
      genres=genres,
      image_link=image_link,
      facebook_link=facebook_link,
      website_link=website_link,
      seeking_talent=seeking_talent,
      seeking_description=seeking_description,
    )
    db.session.add(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash("An error occurred. Venue " + name + " could not be listed.")

  if not error:
    flash("Venue " + name + " was successfully listed!")

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())  
  finally:
    db.session.close()  

  if error:
    flash("Something went wrong and we couldn't deleted the venue!")

  if not error:
    flash("Venue was successfully deleted!")

  return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  data = []

  for artist in artists:
    data.append({"id": artist.id, "name": artist.name})

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()
  data = []

  for artist in artists:
    upcoming_shows = Artist.query \
        .join(Shows) \
        .filter(Shows.c.artist_id == artist.id) \
        .filter(Shows.c.start_time > datetime.now()) \
        .all()
    data.append({
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': len(upcoming_shows)
    })

  response = {
    'data': data,
    'count': len(artists)
  }      
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.filter_by(id=artist_id).first()
  shows = db.session.query(Shows).filter(Shows.c.artist_id == artist.id).all()
  upcoming_shows = []
  past_shows = []
  
  for show in shows:
    venue = Venue.query.filter_by(id=show.venue_id).first()
    if(show.start_time >= datetime.now()):
      upcoming_shows.append({
        'venue_id': venue.id,
        'venue_name': venue.name,
        'venue_image_link': venue.image_link,
        'start_time': format_datetime(str(show.start_time)),
      })
    else:
      past_shows.append({
          'venue_id': venue.id,
          'venue_name': venue.name,
          'venue_image_link': venue.image_link,
          'start_time': format_datetime(str(show.start_time)),
      })

  #append upcoming shows    
  artist.upcoming_shows  = upcoming_shows
  artist.upcoming_shows_count = len(upcoming_shows) 

  #append past shows    
  artist.past_shows = past_shows
  artist.past_shows_count = len(past_shows) 

  return render_template('pages/show_artist.html', artist=artist)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.filter_by(id=artist_id).first()

  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.genres.data = artist.genres
  form.image_link.data = artist.image_link
  form.facebook_link.data = artist.facebook_link
  form.website_link.data = artist.website_link
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  error = False
  name = request.form['name']
  city = request.form['city']
  state = request.form['state']
  phone = request.form['phone']
  genres = request.form.getlist('genres')
  image_link = request.form['image_link']
  facebook_link = request.form['facebook_link']
  website_link = request.form['website_link']
  seeking_venue = True if 'seeking_venue' in request.form else False
  seeking_description = request.form['seeking_description']

  try:
    artist = Artist.query.filter_by(id=artist_id).first()

    artist.name = name
    artist.city = city
    artist.state = state
    artist.phone = phone
    artist.genres = genres
    artist.image_link = image_link
    artist.facebook_link = facebook_link
    artist.website_link = website_link
    artist.seeking_venue = seeking_venue
    artist.seeking_description = seeking_description

    db.session.commit()
  except Exception:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Artist ' + name + ' could not be updated.')
  if not error:
    flash('Artist ' + name + ' was successfully updated!')

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.filter_by(id=venue_id).first()

  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.genres.data = venue.genres
  form.image_link.data = venue.image_link
  form.facebook_link.data = venue.facebook_link
  form.website_link.data = venue.website_link
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False
  name = request.form['name']
  city = request.form['city']
  state = request.form['state']
  address = request.form['address']
  phone = request.form['phone']
  genres = request.form.getlist('genres')
  image_link = request.form['image_link']
  facebook_link = request.form['facebook_link']
  website_link = request.form['website_link']
  seeking_talent = True if 'seeking_talent' in request.form else False
  seeking_description = request.form['seeking_description']

  try:
    venue = Venue.query.filter_by(id=venue_id).first()

    venue.name = name
    venue.city = city
    venue.state = state
    venue.address = address
    venue.phone = phone
    venue.genres = genres
    venue.image_link = image_link
    venue.facebook_link = facebook_link
    venue.website_link = website_link
    venue.seeking_talent = seeking_talent
    venue.seeking_description = seeking_description

    db.session.commit()
  except Exception:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Venue ' + name + ' could not be updated.')
  if not error:
    flash('Venue ' + name + ' was successfully updated!')
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  name = request.form['name']
  city = request.form['city']
  state = request.form['state']
  phone = request.form['phone']
  genres = request.form.getlist('genres')
  image_link = request.form['image_link']
  facebook_link = request.form['facebook_link']
  website_link = request.form['website_link']
  seeking_venue = True if 'seeking_venue' in request.form else False
  seeking_description = request.form['seeking_description']

  try:
    artist = Artist(
      name=name,
      city=city,
      state=state,
      phone=phone,
      genres=genres,
      image_link=image_link,
      facebook_link=facebook_link,
      website_link=website_link,
      seeking_venue=seeking_venue,
      seeking_description=seeking_description,
    )
    db.session.add(artist)
    db.session.commit()
  except Exception:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Artist ' + name + ' could not be listed.')
  if not error:
    flash('Artist ' + name + ' was successfully listed!')
    
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = db.session.query(Shows).all()
  data = []
  for show in shows:
    artist = Artist.query.filter_by(id=show.artist_id).first()
    venue = Venue.query.filter_by(id=show.venue_id).first()
    data.append({
      "venue_id": show.id,
      "venue_name": venue.name,
      "artist_id": artist.id,
      "artist_name":artist.name,
      "artist_image_link": artist.image_link,
      "start_time": str(show.start_time)
    })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False 
  artist_id = request.form['artist_id']
  venue_id = request.form['venue_id']
  start_time = request.form['start_time']
  try:
    show = Shows.insert().values(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
    db.session.execute(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Show could not be listed.')
  if not error:
    flash('Show was successfully listed!')
  
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
