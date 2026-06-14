import os

# Create directories
os.makedirs('accounts/templates/accounts', exist_ok=True)

# ==========================================
# LOGIN TEMPLATE
# ==========================================
login_html = """<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h3 class="text-center mb-4">Login</h3>
                        {% if messages %}
                            {% for message in messages %}
                                <div class="alert alert-{{ message.tags }}">{{ message }}</div>
                            {% endfor %}
                        {% endif %}
                        <form method="POST">
                            {% csrf_token %}
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login</button>
                        </form>
                        <hr>
                        <p class="text-center">
                            <a href="/accounts/register/player/">Register as Player</a> |
                            <a href="/accounts/register/venue-owner/">Register as Venue Owner</a>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

# ==========================================
# REGISTER PLAYER TEMPLATE
# ==========================================
register_player_html = """<!DOCTYPE html>
<html>
<head>
    <title>Register as Player</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h3 class="text-center mb-4">Register as Player</h3>
                        {% if messages %}
                            {% for message in messages %}
                                <div class="alert alert-{{ message.tags }}">{{ message }}</div>
                            {% endfor %}
                        {% endif %}
                        <form method="POST">
                            {% csrf_token %}
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="email" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Full Name</label>
                                <input type="text" name="full_name" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Phone</label>
                                <input type="text" name="phone" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>City</label>
                                <input type="text" name="city" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Register</button>
                        </form>
                        <p class="text-center mt-3">
                            Already have an account? <a href="/accounts/login/">Login</a>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

# ==========================================
# REGISTER VENUE OWNER TEMPLATE
# ==========================================
register_owner_html = """<!DOCTYPE html>
<html>
<head>
    <title>Register as Venue Owner</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h3 class="text-center mb-4">Register as Venue Owner</h3>
                        {% if messages %}
                            {% for message in messages %}
                                <div class="alert alert-{{ message.tags }}">{{ message }}</div>
                            {% endfor %}
                        {% endif %}
                        <form method="POST">
                            {% csrf_token %}
                            <div class="mb-3">
                                <label>Email</label>
                                <input type="email" name="email" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Full Name</label>
                                <input type="text" name="full_name" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Phone</label>
                                <input type="text" name="phone" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Business Name</label>
                                <input type="text" name="business_name" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Business Address</label>
                                <textarea name="business_address" class="form-control" required></textarea>
                            </div>
                            <div class="mb-3">
                                <label>Business City</label>
                                <input type="text" name="business_city" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Register</button>
                        </form>
                        <p class="text-center mt-3">
                            Already have an account? <a href="/accounts/login/">Login</a>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

# Write all files
with open('accounts/templates/accounts/login.html', 'w', encoding='utf-8') as f:
    f.write(login_html)
print("✅ login.html created")

with open('accounts/templates/accounts/register_player.html', 'w', encoding='utf-8') as f:
    f.write(register_player_html)
print("✅ register_player.html created")

with open('accounts/templates/accounts/register_venue_owner.html', 'w', encoding='utf-8') as f:
    f.write(register_owner_html)
print("✅ register_venue_owner.html created")

print("\n🎉 All templates created successfully!")