from global_travel.database import Database
db = Database("global_travel/data/global_travel.db")
print(db.get_all_bookings())