# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) # DON'T CHANGE THIS !!!

from src.database import db
from datetime import datetime

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    client_number = db.Column(db.String(50), nullable=False)
    service_tag = db.Column(db.String(100), nullable=False)
    service_details = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False) # Duration in days
    main_price = db.Column(db.Float, nullable=False)
    additional_costs = db.Column(db.Float, nullable=False, default=0.0)
    client_type = db.Column(db.String(50), nullable=False)
    installments = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Key to link to the User who created this client record
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Client {self.client_name}>'

