from api.auth import auth_bp
from api.payments import payments_bp
from api.valuations import valuations_bp
from api.inspections import inspections_bp
from api.intelligence import intelligence_bp
from api.webhooks import webhooks_bp
from api.mileage import mileage_bp  # ✅ included

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(payments_bp, url_prefix='/api/payments')
app.register_blueprint(valuations_bp, url_prefix='/api/valuations')
app.register_blueprint(inspections_bp, url_prefix='/api/inspections')
app.register_blueprint(intelligence_bp, url_prefix='/api/intelligence')
app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
app.register_blueprint(mileage_bp, url_prefix='/api/mileage')
