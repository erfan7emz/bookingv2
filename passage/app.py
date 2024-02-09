from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Consultant, Time, Booking
from datetime import datetime, time
from sqlalchemy import and_, or_
import os

def create_app():
    app = Flask(__name__)
    load_dotenv()
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    CORS(app)
    db.init_app(app)
    
    with app.app_context():
        db.create_all()

    return app

app = create_app()

# create a consultant
@app.route('/consultant', methods=['POST'])
def add_consultant():
    try:
        data = request.get_json()
        new_consultant = Consultant(username=data['username'])
        db.session.add(new_consultant)
        db.session.commit()
        return jsonify({'message': 'Consultant created successfully'}), 201
    except Exception as e:
        return jsonify({'error': 'An error occurred'}), 500

# create an available time slot for a consultant
@app.route('/time', methods=['POST'])
def add_time():
    data = request.get_json()

    start_time_format = '%d-%m-%Y:%H:%M'
    end_time_format = '%d-%m-%Y:%H:%M'

    start_time = datetime.strptime(data['start_time'], start_time_format)
    end_time = datetime.strptime(data['end_time'], end_time_format)

    new_time = Time(start_time=start_time, end_time = end_time, consultant_id = data['consultant_id'])
    db.session.add(new_time)
    db.session.commit()
    return jsonify({'message': 'Time created successfully'}), 201

# get all available time slots of a consultant
@app.route('/consultant/<int:cons_id>/times', methods=['GET'])
def get_all_times(cons_id):
    cons = Consultant.query.get(cons_id)
    if not cons:
        return jsonify({'message': 'Consultant not found'}), 404
    
    # print(cons)
    response = [
        {'start_time': time.start_time.strftime('%d-%m-%Y:%H:%M'), 
         'end_time': time.end_time.strftime('%d-%m-%Y:%H:%M')}
        for time in cons.available_times
    ]
    return jsonify(response), 200

# get all available and not booked time slots for a specific consultant in a specific date
@app.route('/consultant/<int:consultant_id>/available-times', methods=['GET'])
def get_available_times_for_date(consultant_id):
    query_date_str = request.args.get('date')
    if not query_date_str:
        return jsonify({'error': 'Date parameter is required in format YYYY-MM-DD'}), 400

    try:
        query_date = datetime.strptime(query_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    day_start = datetime.combine(query_date, datetime.min.time())
    day_end = datetime.combine(query_date, datetime.max.time())

    consultant_times = Time.query.filter(
        Time.consultant_id == consultant_id,
        Time.start_time <= day_end,
        Time.end_time >= day_start
    ).all()

    booked_times = Booking.query.filter(
        Booking.consultant_id == consultant_id,
        Booking.start_time < day_end,
        Booking.end_time > day_start
    ).all()

    available_times = []
    for time_slot in consultant_times:
        print(time_slot)
        if not any(time_slot.start_time < booking.end_time and time_slot.end_time > booking.start_time for booking in booked_times):
            # print(available_times)
            available_times.append({
                'start_time': max(time_slot.start_time, day_start).strftime('%Y-%m-%d %H:%M'),
                'end_time': min(time_slot.end_time, day_end).strftime('%Y-%m-%d %H:%M')
            })

    return jsonify(available_times), 200


# book a time slot
@app.route('/consultant/<int:consultant_id>/book', methods=['POST'])
def book_specific_time(consultant_id):
    data = request.get_json()
    requested_start_time = datetime.strptime(data['start_time'], '%Y-%m-%d %H:%M')
    requested_end_time = datetime.strptime(data['end_time'], '%Y-%m-%d %H:%M')
    client_name = data['client_name']

    is_within_available_times = Time.query.filter(
        Time.consultant_id == consultant_id,
        Time.start_time <= requested_start_time,
        Time.end_time >= requested_end_time
    ).first()

    # print(is_within_available_times)

    if not is_within_available_times:
        return jsonify({'error': 'consultant not available at this time'}), 400

    overlapping_bookings = Booking.query.filter(
        Booking.consultant_id == consultant_id,
        or_(
            and_(Booking.start_time < requested_end_time, Booking.end_time > requested_start_time)
        )
    ).first()

    # print(overlapping_bookings)

    if overlapping_bookings:
        return jsonify({'error': 'this time overlaps with an existing booking'}), 400

    new_booking = Booking(
        client_name=client_name,
        start_time=requested_start_time,
        end_time=requested_end_time,
        consultant_id=consultant_id
    )
    print(new_booking.consultant_id)
    
    db.session.add(new_booking)
    db.session.commit()

    return jsonify({'message': 'Booking successfully created'}), 201


if __name__ == '__main__':
    app.run(port=8080)
