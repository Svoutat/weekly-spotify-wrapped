# Weekly Spotify Wrapped

Python automation project for module M122E.

The program creates a personal weekly music recap from Last.fm listening data. It enriches the tracks with Spotify metadata, stores the listening history in SQLite, generates a dark Spotify-style HTML report and can send the report by email through Gmail SMTP.

## Features

- Fetches Last.fm tracks for the configured period.
- Stores track plays locally in SQLite and prevents duplicates.
- Enriches tracks with Spotify links, durations, album covers and artist images.
- Calculates top songs, top artists, track count, unique tracks, unique artists and listening time.
- Compares the current week with the previous week using the database history.
- Generates an HTML report in `output/`.
- Sends the weekly report by email if `SEND_EMAIL=true`.
- Optionally creates or updates a Spotify playlist.
- Keeps secrets outside the code in `.env`.
- Includes pytest tests for every application module.

## Project Structure

```text
spotify_weekly_wrapped/
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
|   |-- M122E_Final_Documentation.md
|   |-- M122E_Test_Protocol.md
|   |-- M122E_Project_Plan_Spotify_Wrapped.xlsx
|   |-- ProjectProposalM122E.docx
|   |-- diagrams/
|-- output/
```

## Setup

Clone the repository or open PowerShell in the project folder:

```powershell
git clone https://github.com/Svoutat/weekly-spotify-wrapped.git
cd spotify_weekly_wrapped
```

For the local school folder:

```powershell
cd C:\Users\voutats1\Documents\Gibz\Informatik\M122\M122ESpotifyProject\spotify_weekly_wrapped
```

Then install the project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Then fill the values in `.env`.

## Environment Values

| Value | Required | How to get it |
| --- | --- | --- |
| `LASTFM_API_KEY` | Yes | Create an API account at `https://www.last.fm/api/account/create`. |
| `LASTFM_USERNAME` | Yes | Your Last.fm username from your profile. |
| `SPOTIFY_CLIENT_ID` | Recommended | Spotify Developer Dashboard: `https://developer.spotify.com/dashboard`. |
| `SPOTIFY_CLIENT_SECRET` | Recommended | Same Spotify app, button "View client secret". |
| `SPOTIFY_REDIRECT_URI` | For setup helper | Add `http://127.0.0.1:8888/callback` in the Spotify app redirect URIs. |
| `SPOTIFY_REFRESH_TOKEN` | Optional | Run `python spotify_setup.py` after client ID/secret are set. |
| `SPOTIFY_PLAYLIST_ID` | Optional | Created or saved by `python spotify_setup.py`. |
| `PLAYLIST_URL` | Optional | Created or saved by `python spotify_setup.py`. |
| `ENABLE_PLAYLIST` | Optional | Use `true` only if playlist permissions work. |
| `GMAIL_ADDRESS` | If email enabled | Gmail address used for sending. |
| `GMAIL_APP_PASSWORD` | If email enabled | Google account app password, not the normal Gmail password. |
| `RECIPIENT_EMAIL` | If email enabled | Email address that receives the report. |
| `SEND_EMAIL` | No | `true` sends the email, `false` only creates the HTML report. |
| `LOOKBACK_DAYS` | No | Default is `7`. The app loads enough history to compare with the previous week. |
| `DATABASE_PATH` | No | Default is `spotify_wrapped.sqlite3`. |
| `OUTPUT_DIR` | No | Default is `output`. |

### Last.fm

1. Open `https://www.last.fm/api/account/create`.
2. Create an API application.
3. Copy the API key into `.env`.
4. Add your Last.fm username.

The Last.fm API secret is not needed for this project because the script only reads recent public scrobbles.

### Spotify

1. Open `https://developer.spotify.com/dashboard`.
2. Create an app.
3. Add this redirect URI: `http://127.0.0.1:8888/callback`.
4. Copy the client ID and client secret into `.env`.
5. Run:

```powershell
python spotify_setup.py
```

The helper prints an authorization link, receives the Spotify callback locally and writes the refresh token and playlist values to `.env`.

If Spotify playlist updates return HTTP 403, set `ENABLE_PLAYLIST=false`. The report still works because Spotify enrichment and playlist updates are optional.

### Gmail

1. Enable 2-Step Verification in the Google account.
2. Open `https://myaccount.google.com/apppasswords`.
3. Create an app password.
4. Put the generated app password into `GMAIL_APP_PASSWORD`.

Do not use the normal Gmail password.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Result:

- SQLite database is created or updated.
- HTML report is saved in `output/`.
- Email is sent if `SEND_EMAIL=true`.
- Playlist is updated only if `ENABLE_PLAYLIST=true` and Spotify permissions are valid.

## Weekly Automation

On Windows, use Task Scheduler:

```text
Program:
C:\Users\voutats1\Documents\Gibz\Informatik\M122\M122ESpotifyProject\spotify_weekly_wrapped\.venv\Scripts\python.exe

Arguments:
main.py

Start in:
C:\Users\voutats1\Documents\Gibz\Informatik\M122\M122ESpotifyProject\spotify_weekly_wrapped
```

Schedule it once per week. The task will run the same workflow as `python main.py`.

## Tests

Run all tests:

```powershell
python -m pytest
```

Latest verified result:

```text
35 passed
```

The tests cover configuration, database behavior, Last.fm loading, Spotify enrichment, Spotify setup, report generation, email sending, the main workflow and project structure.

## Documentation

The final school documentation is in `docs/`:

- `M122E_Final_Documentation.docx`
- `M122E_Final_Documentation.md`
- `M122E_Test_Protocol.md`
- `M122E_Project_Plan_Spotify_Wrapped.xlsx`
- `ProjectProposalM122E.docx`
- `diagrams/`

For grading, the main document to open is `docs/M122E_Final_Documentation.docx`. The README is only the short project and setup guide.

## Submission Notes

Submit the source code, tests, `requirements.txt`, `.env.example`, README and documentation.

When submitting through GitHub, commit the project files and send the public repository link. The files below must stay local and must not be committed.

Do not submit:

- `.env`
- `.venv/`
- `spotify_wrapped.sqlite3`
- generated files in `output/`
- `__pycache__/`
- `.pytest_cache/`

These files are local runtime files or contain private information.
