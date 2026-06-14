import os

# Create all directories
dirs = [
    'venues/templates/venues',
    'booking/templates/booking',
    'teams/templates/teams',
    'tournaments/templates/tournaments',
]
for d in dirs:
    os.makedirs(d, exist_ok=True)

# ==========================================
# VENUE TEMPLATES
# ==========================================
with open('venues/templates/venues/venue_list.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}My Venues{% endblock %}
{% block content %}
<div class="row">
    <div class="col-12">
        <h1>My Venues</h1>
        <a href="/venues/create/" class="btn btn-primary mb-3">Add New Venue</a>
        <hr>
    </div>
</div>
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-body">
                <p>No venues yet. Click "Add New Venue" to get started.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")

with open('venues/templates/venues/booking_requests.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Booking Requests{% endblock %}
{% block content %}
<h1>Booking Requests</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p>No booking requests yet.</p>
    </div>
</div>
{% endblock %}""")

# ==========================================
# BOOKING TEMPLATES
# ==========================================
with open('booking/templates/booking/field_browse.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Browse Fields{% endblock %}
{% block content %}
<h1>Browse Fields</h1>
<hr>
<div class="row">
    <div class="col-md-3">
        <div class="card">
            <div class="card-header">Filters</div>
            <div class="card-body">
                <form method="GET">
                    <div class="mb-3">
                        <label>Sport Type</label>
                        <select name="sport_type" class="form-control">
                            <option value="">All Sports</option>
                            <option>Football</option>
                            <option>Cricket</option>
                            <option>Basketball</option>
                            <option>Tennis</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label>City</label>
                        <input type="text" name="city" class="form-control" placeholder="City">
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Search</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-9">
        <div class="card">
            <div class="card-body">
                <p>No fields found. Try different filters.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")

with open('booking/templates/booking/field_detail.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Field Details{% endblock %}
{% block content %}
<h1>Field Details</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p>Field information will be displayed here.</p>
    </div>
</div>
{% endblock %}""")

with open('booking/templates/booking/booking_form.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Book Field{% endblock %}
{% block content %}
<h1>Book Field</h1>
<hr>
<div class="card">
    <div class="card-body">
        <form method="POST">
            {% csrf_token %}
            <p>Booking form will be here.</p>
        </form>
    </div>
</div>
{% endblock %}""")

with open('booking/templates/booking/booking_history.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Booking History{% endblock %}
{% block content %}
<h1>My Bookings</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p>No bookings yet.</p>
    </div>
</div>
{% endblock %}""")

# ==========================================
# TEAMS TEMPLATES
# ==========================================
with open('teams/templates/teams/team_list.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}My Teams{% endblock %}
{% block content %}
<h1>My Teams</h1>
<hr>
<a href="/teams/create/" class="btn btn-primary mb-3">Create Team</a>
<a href="/teams/find/" class="btn btn-success mb-3">Find Teams</a>
<div class="card">
    <div class="card-body">
        <p>You haven't joined any teams yet.</p>
    </div>
</div>
{% endblock %}""")

with open('teams/templates/teams/find_teams.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Find Teams{% endblock %}
{% block content %}
<h1>Find Teams</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p>Search for teams to join.</p>
    </div>
</div>
{% endblock %}""")

# ==========================================
# TOURNAMENTS TEMPLATES
# ==========================================
with open('tournaments/templates/tournaments/tournament_list.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Tournaments{% endblock %}
{% block content %}
<h1>Tournaments</h1>
<hr>
<div class="row">
    <div class="col-12">
        <div class="card">
            <div class="card-body">
                <p>No tournaments available yet.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")

with open('tournaments/templates/tournaments/tournament_detail.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Tournament Details{% endblock %}
{% block content %}
<h1>Tournament Details</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p>Tournament information will be displayed here.</p>
    </div>
</div>
{% endblock %}""")

# ==========================================
# PROFILE TEMPLATE
# ==========================================
with open('accounts/templates/accounts/profile.html', 'w', encoding='utf-8') as f:
    f.write("""{% extends 'base.html' %}
{% block title %}Profile{% endblock %}
{% block content %}
<h1>My Profile</h1>
<hr>
<div class="card">
    <div class="card-body">
        <p><strong>Email:</strong> {{ user.email }}</p>
        <p><strong>Role:</strong> {{ user.get_role_display }}</p>
        <a href="/accounts/profile/edit/" class="btn btn-primary">Edit Profile</a>
    </div>
</div>
{% endblock %}""")

print("✅ All templates created successfully!")
print("\nTemplates created for:")
print("  - venues (venue_list, booking_requests)")
print("  - booking (browse, detail, form, history)")
print("  - teams (list, find)")
print("  - tournaments (list, detail)")
print("  - accounts (profile)")