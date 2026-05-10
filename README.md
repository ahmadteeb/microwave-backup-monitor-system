# MW Backup Monitor System

A Flask + Vanilla JS SPA for real-time monitoring of microwave backup links in a NOC environment.

## Development

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Run the development server:
   ```bash
   python run.py
   ```
3. Open `http://127.0.0.1:5000`.

## Production

Start with Gunicorn:

```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

## Notes

- `instance/` and `secrets/` are omitted from source control by `.gitignore`.
- Use `gunicorn.conf.py` for production process management.
