# Auth Testing Playbook — AeroPulse

## MongoDB Verification
```bash
mongosh
use test_database
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
- bcrypt hash starts with `$2b$`
- Indexes: `users.email` (unique), `login_attempts.identifier`, `password_reset_tokens.expires_at` (TTL)

## API Testing
```bash
curl -c cookies.txt -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@aqi.io","password":"pass1234","name":"Tester"}'

curl -c cookies.txt -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@aqi.io","password":"admin123"}'

curl -b cookies.txt http://localhost:8001/api/auth/me

curl -b cookies.txt -X POST http://localhost:8001/api/auth/logout
```

## Endpoints
- POST `/api/auth/register` — creates user, sets cookies, returns user
- POST `/api/auth/login`   — validates password, sets cookies, returns user
- POST `/api/auth/logout`  — clears cookies
- GET  `/api/auth/me`      — returns current user via cookie
- POST `/api/auth/refresh` — refreshes access token from refresh cookie
- POST `/api/auth/forgot-password` — logs a reset token to backend logs
- POST `/api/auth/reset-password`  — { token, password }

## Test Accounts
- Admin: `admin@aqi.io` / `admin123` (auto-seeded)
- Register any new user via `/register`
