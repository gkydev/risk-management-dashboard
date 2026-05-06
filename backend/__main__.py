from __future__ import annotations

import os

from backend.app import create_app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG") == "1")
