# Weekly Spotify Wrapped

M122E Python automation project.

Weekly Spotify Wrapped creates a personal weekly music report from Last.fm listening data. The program enriches tracks with Spotify metadata, stores the listening history in SQLite, generates a Spotify-style HTML report and can send it by email through Gmail SMTP.

## 1. Features

- Loads weekly listening history from Last.fm.
- Enriches tracks with Spotify links, durations, album covers and artist images.
- Stores listening history in SQLite and prevents duplicate track plays.
- Calculates top songs, top artists, total tracks, unique tracks, unique artists and listening time.
- Compares the current week with the previous week.
- Generates an HTML report in `output/`.
- Sends the report by email when `SEND_EMAIL=true`.
- Optionally creates or updates a Spotify playlist.
- Uses `.env` for secrets and configuration.
- Includes pytest tests for every application module.

## 2. Project Structure

```text
weekly-spotify-wrapped/
|-- main.py
|-- config.py
|-- database.py
|-- lastfm_client.py
|-- spotify_client.py
|-- spotify_setup.py
|-- report_generator.py
|-- email_sender.py
|-- requirements.txt
|-- .env.example
|-- tests/
|-- docs/
|   |-- M122E_Final_Documentation.docx
|   |-- M122E_Final_Documentation.pdf
|   |-- M122E_Test_Protocol.docx
|   |-- M122E_Test_Protocol.pdf
|   |-- M122E_Project_Plan_Spotify_Wrapped.xlsx
|   |-- M122E_Project_Plan_Spotify_Wrapped.pdf
|   |-- ProjectProposalM122E.docx
|   |-- ProjectProposalM122E.pdf
|   |-- assets/
|   |-- diagrams/
|-- output/
```

## 3. Setup

### 3.1 Clone The Repository

```powershell
git clone https://github.com/Svoutat/weekly-spotify-wrapped.git
cd weekly-spotify-wrapped
```

If the project is already stored locally, open PowerShell in the existing project folder instead:

```powershell
cd <project-path>
```

### 3.2 Create The Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3.3 Create The `.env` File

```powershell
Copy-Item .env.example .env
```

Fill the values in `.env`. Never commit the real `.env` file.

## 4. Environment Values

| Value | Required | Description |
| --- | --- | --- |
| `LASTFM_API_KEY` | Yes | Last.fm API key from `https://www.last.fm/api/account/create`. |
| `LASTFM_USERNAME` | Yes | Last.fm username whose scrobbles should be loaded. |
| `SPOTIFY_CLIENT_ID` | Recommended | Spotify app client ID. |
| `SPOTIFY_CLIENT_SECRET` | Recommended | Spotify app client secret. |
| `SPOTIFY_REDIRECT_URI` | For setup helper | Use `http://127.0.0.1:8888/callback`. |
| `SPOTIFY_REFRESH_TOKEN` | Optional | Created by `python spotify_setup.py` for playlist updates. |
| `SPOTIFY_PLAYLIST_ID` | Optional | Existing or generated Spotify playlist ID. |
| `PLAYLIST_URL` | Optional | Link to the generated playlist. |
| `ENABLE_PLAYLIST` | Optional | Set to `true` only if playlist permissions work. |
| `GMAIL_ADDRESS` | If email enabled | Gmail sender address. |
| `GMAIL_APP_PASSWORD` | If email enabled | Google app password, not the normal Gmail password. |
| `RECIPIENT_EMAIL` | If email enabled | Email address that receives the report. |
| `SEND_EMAIL` | No | `true` sends email, `false` only creates the HTML report. |
| `LOOKBACK_DAYS` | No | Default is `7`. |
| `DATABASE_PATH` | No | Default is `spotify_wrapped.sqlite3`. |
| `OUTPUT_DIR` | No | Default is `output`. |

## 5. API Setup

### 5.1 Last.fm

1. Open `https://www.last.fm/api/account/create`.
2. Create an API application.
3. Copy the API key into `LASTFM_API_KEY`.
4. Add your Last.fm username to `LASTFM_USERNAME`.

The Last.fm API secret is not needed because the program only reads recent public scrobbles.

### 5.2 Spotify

1. Open `https://developer.spotify.com/dashboard`.
2. Create a Spotify app.
3. Add `http://127.0.0.1:8888/callback` as redirect URI.
4. Copy the client ID and client secret into `.env`.
5. Run the setup helper if playlist updates should be used:

```powershell
python spotify_setup.py
```

If Spotify playlist updates return HTTP 403, set `ENABLE_PLAYLIST=false`. The report still works without playlist updates.

### 5.3 Gmail

1. Enable 2-Step Verification in the Google account.
2. Open `https://myaccount.google.com/apppasswords`.
3. Create an app password.
4. Put the generated app password into `GMAIL_APP_PASSWORD`.

Use the app password, not the normal Gmail password.

## 6. Run The Program

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Expected result:

- SQLite database is created or updated.
- Last.fm tracks are loaded.
- Spotify metadata is added if Spotify is configured.
- HTML report is saved in `output/`.
- Email is sent if `SEND_EMAIL=true`.
- Playlist is updated only if `ENABLE_PLAYLIST=true`.

## 7. Weekly Automation

Use Windows Task Scheduler for weekly automatic execution.

Program:

```text
<project-path>\.venv\Scripts\python.exe
```

Arguments:

```text
main.py
```

Start in:

```text
<project-path>
```

Replace `<project-path>` with the folder where the repository was cloned.

## 8. Tests

```powershell
python -m pytest
```

Latest verified result:

```text
37 passed
```

## 9. Documentation

The main documentation is in `docs/`.

For grading, open:

- `docs/M122E_Final_Documentation.pdf`
- `docs/M122E_Final_Documentation.docx`

Additional evidence:

- `docs/M122E_Test_Protocol.pdf`
- `docs/M122E_Project_Plan_Spotify_Wrapped.pdf`
- `docs/ProjectProposalM122E.pdf`
- `docs/assets/`
- `docs/diagrams/`

## 10. Submission Notes

Submit the GitHub repository link:

```text
https://github.com/Svoutat/weekly-spotify-wrapped
```

Do not submit or commit:

- `.env`
- `.venv/`
- `spotify_wrapped.sqlite3`
- generated HTML reports in `output/`
- `__pycache__/`
- `.pytest_cache/`

These files are local runtime files or contain private information.
