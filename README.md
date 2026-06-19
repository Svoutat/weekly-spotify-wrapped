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
|-- .github/
|   |-- workflows/
|       |-- ci.yml
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
| `GMAIL_ADDRESS` | Only if email is enabled | Gmail sender address. Leave empty when `SEND_EMAIL=false`. |
| `GMAIL_APP_PASSWORD` | Only if email is enabled | Google app password, not the normal Gmail password. Leave empty when `SEND_EMAIL=false`. |
| `RECIPIENT_EMAIL` | Only if email is enabled | Email address that receives the report. Leave empty when `SEND_EMAIL=false`. |
| `SEND_EMAIL` | No | `true` sends email, `false` only creates the HTML report. Email setup is optional. |
| `LOOKBACK_DAYS` | No | Default is `7`. |
| `DATABASE_PATH` | No | Default is `spotify_wrapped.sqlite3`. |
| `OUTPUT_DIR` | No | Default is `output`. |

## 5. API Setup

### 5.1 Last.fm

1. Open `https://www.last.fm/api/account/create`.
2. Log in with a Last.fm account.
3. Create an API application.
4. Use a clear application name, for example `Weekly Spotify Wrapped`.
5. Use a short description such as `Weekly listening report for a school automation project`.
6. The callback URL and homepage are not needed for this project. If Last.fm asks for a URL, a placeholder such as `http://localhost` can be used.
7. Copy the generated API key into `LASTFM_API_KEY`.
8. Add the Last.fm username whose scrobbles should be loaded to `LASTFM_USERNAME`.

The Last.fm API secret is not needed because the program only reads recent public scrobbles.

### 5.2 Spotify

Spotify is recommended for covers, artist images, durations and Spotify links. According to Spotify's Web API Getting Started page, a Spotify Premium account can be required to use the Web API. If the teacher does not have Spotify Premium or does not want to create a Spotify app, the project can still be tested without Spotify by leaving the Spotify values empty and setting `ENABLE_PLAYLIST=false`.

With Spotify Premium or a working Spotify Developer account:

1. Open `https://developer.spotify.com/dashboard`.
2. Log in with a Spotify account.
3. Click **Create app**.
4. Use an app name such as `Weekly Spotify Wrapped`.
5. Use a description such as `Weekly music report using Spotify metadata`.
6. Enter `http://127.0.0.1:8888/callback` as redirect URI. This must match `SPOTIFY_REDIRECT_URI` in `.env`.
7. Select **Web API** as the API or SDK.
8. Accept the Spotify developer terms and create the app.
9. Open the app settings.
10. Copy the client ID into `SPOTIFY_CLIENT_ID`.
11. Click **View client secret** and copy it into `SPOTIFY_CLIENT_SECRET`.
12. Spotify metadata enrichment works with only client ID and client secret. The report can run without playlist permissions.
13. Run the setup helper only if playlist updates should be used:

```powershell
python spotify_setup.py
```

The setup helper opens a Spotify login URL. After login, Spotify redirects to the local callback URL. The helper then saves the generated values for `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_PLAYLIST_ID` and `PLAYLIST_URL` in `.env`.

Alternative without Spotify Premium:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REFRESH_TOKEN=
SPOTIFY_PLAYLIST_ID=
PLAYLIST_URL=
ENABLE_PLAYLIST=false
```

In this mode, the program uses Last.fm data only. The database, statistics, HTML report, tests and optional email sending still work. Album covers, Spotify links, Spotify durations and playlist updates are simply skipped.

If Spotify playlist updates return HTTP 403, set `ENABLE_PLAYLIST=false`. The report still works without playlist updates. This is the recommended setting for a simple teacher test when playlist permissions are not needed.

### 5.3 Gmail

Email sending is optional. If the teacher only wants to test report generation, use:

```env
SEND_EMAIL=false
```

With this setting, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` and `RECIPIENT_EMAIL` can stay empty. The program still creates the HTML report in `output/`.

To test email delivery:

1. Use a Gmail account as the sender.
2. Enable 2-Step Verification in the Google account.
3. Open `https://myaccount.google.com/apppasswords`.
4. Create an app password for this project.
5. Put the Gmail address into `GMAIL_ADDRESS`.
6. Put the generated app password into `GMAIL_APP_PASSWORD`.
7. Put the receiver email address into `RECIPIENT_EMAIL`.
8. Set `SEND_EMAIL=true`.

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

## 9. CI/CD Pipeline

The repository includes a GitHub Actions workflow in `.github/workflows/ci.yml`.

The pipeline runs automatically on pushes and pull requests to `main`:

1. Check out the repository.
2. Set up Python 3.12.
3. Install dependencies from `requirements.txt`.
4. Run `python -m pytest`.

This is a CI pipeline for the school project. There is no real production deployment, so the CD part is limited to keeping the repository in an automatically tested, submission-ready state.

## 10. Documentation

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

## 11. Submission Notes

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
