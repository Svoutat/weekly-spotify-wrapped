# M122E Test Protocol - Weekly Spotify Wrapped

## Test Environment

| Item | Value |
| --- | --- |
| Operating system | Windows |
| Python | Python 3.14.3 |
| Test framework | pytest |
| Project folder | `spotify_weekly_wrapped` |
| Main command | `python main.py` |
| Test command | `python -m pytest` |

## Automated Unit Tests

| Test ID | Test Case | File | Expected Result | Status |
| --- | --- | --- | --- | --- |
| T-01 | Load config with required Last.fm values and email disabled. | `tests/test_config.py` | Config object is created successfully. | Passed |
| T-02 | Missing Last.fm values are detected. | `tests/test_config.py` | `ConfigError` mentions missing Last.fm fields. | Passed |
| T-03 | Gmail values are required when `SEND_EMAIL=true`. | `tests/test_config.py` | `ConfigError` mentions Gmail fields. | Passed |
| T-04 | Spotify is enabled when client ID and secret exist. | `tests/test_config.py` | `spotify_enabled` is `True`. | Passed |
| T-05 | UTF-8 BOM `.env` files are supported. | `tests/test_config.py` | Config loads correctly. | Passed |
| T-06 | Database prevents duplicate tracks. | `tests/test_database.py` | One insert, one duplicate skip. | Passed |
| T-07 | Database fetches only tracks inside the requested period. | `tests/test_database.py` | Only in-range track is returned. | Passed |
| T-08 | Duplicate track can receive Spotify metadata. | `tests/test_database.py` | Existing row is updated with metadata. | Passed |
| T-09 | Statistics calculate top songs, top artists and listening time. | `tests/test_report_generator.py` | Stats values match expected sample data. | Passed |
| T-10 | HTML report is generated and saved. | `tests/test_report_generator.py` | Report file exists and contains expected content. | Passed |
| T-10a | Week-over-week comparison calculates percentage changes and music insights. | `tests/test_report_generator.py` | Current week is compared with previous week. | Passed |
| T-10b | Missing previous-week data is handled cleanly. | `tests/test_report_generator.py` | Report shows a useful fallback message. | Passed |
| T-10c | HTML report includes the comparison section. | `tests/test_report_generator.py` | `Compared with last week` appears in the report. | Passed |
| T-11 | Last.fm tracks are normalized, current-playing tracks are skipped and duplicates are removed. | `tests/test_lastfm_client.py` | Clean track dictionaries are returned without duplicate plays. | Passed |
| T-12 | Last.fm API and JSON errors are handled. | `tests/test_lastfm_client.py` | `LastFmError` is raised with a clear message. | Passed |
| T-13 | Spotify enrichment adds track metadata, album cover and artist image. | `tests/test_spotify_client.py` | Enriched track contains Spotify IDs, links, duration and images. | Passed |
| T-14 | Spotify search fallback, playlist update and API error handling are tested. | `tests/test_spotify_client.py` | Fallback search works, playlist IDs are deduplicated and HTTP errors are clear. | Passed |
| T-15 | Gmail email sending builds a multipart email and validates missing values. | `tests/test_email_sender.py` | SMTP is mocked and `EmailDeliveryError` is raised for missing data. | Passed |
| T-16 | Spotify setup helper builds OAuth URLs, updates `.env` safely and saves setup values. | `tests/test_spotify_setup.py` | OAuth parameters and `.env` updates are correct. | Passed |
| T-17 | Main workflow handles invalid config, normal runs and optional playlist failures. | `tests/test_main.py` | Correct exit codes are returned and optional playlist errors do not stop the report. | Passed |
| T-18 | Project structure and test coverage for every application module are verified. | `tests/test_project_structure.py` | Required files exist and every root Python module has a matching test file. | Passed |

Latest automated result:

```text
35 passed
```

## Manual / Live Tests

| Test ID | Test Case | Steps | Expected Result | Actual Result | Status |
| --- | --- | --- | --- | --- | --- |
| L-01 | Missing `.env` handling | Run `python main.py` without required values. | Program prints clear missing-value error. | Missing values were listed clearly. | Passed |
| L-02 | Last.fm API fetch | Run `python main.py` with valid Last.fm credentials. | Tracks from the configured period are loaded. | Real listening data was loaded successfully. | Passed |
| L-03 | Spotify enrichment | Run `python main.py` with Spotify credentials. | Track metadata is added where possible. | Spotify enrichment completed. | Passed |
| L-04 | SQLite duplicate handling | Run `python main.py` twice. | Second run skips duplicates. | 0 new tracks, 136 duplicates skipped. | Passed |
| L-05 | HTML report generation | Run `python main.py`. | HTML report is saved in `output/`. | A dated `weekly_spotify_wrapped_YYYY-MM-DD.html` report was created. | Passed |
| L-06 | Gmail email delivery | Run `python main.py` with Gmail values. | Report email is delivered. | Email arrived successfully. | Passed |
| L-07 | Optional playlist error handling | Run with playlist enabled. | Playlist errors do not stop report/email. | Spotify returned HTTP 403, report/email still completed. | Passed |
| L-08 | Mobile email preview | Send generated HTML report by email. | Mobile layout is readable and uses hours/covers. | Email was sent with updated dark layout. | Passed |

## Edge Cases Covered

- Missing environment variables.
- UTF-8 BOM in `.env` file.
- Duplicate database records.
- Missing Spotify duration fallback.
- Week-over-week comparison with previous database history.
- Missing previous-week comparison data.
- Spotify playlist permission error.
- Email sending failure path implemented through `EmailDeliveryError`.
- Main workflow behavior without real external services.
- Spotify OAuth setup helper behavior.

## Test Evidence

Important observed log output:

```text
Loaded tracks from Last.fm.
Spotify enrichment finished.
Database saved new tracks and skipped duplicates on repeated runs.
Playlist update failed; continuing without playlist changes: Spotify API request failed with HTTP 403: Forbidden
Report saved to output/weekly_spotify_wrapped_YYYY-MM-DD.html
Weekly report email sent to RECIPIENT_EMAIL.
```

## Test Conclusion

The tests cover all application modules: configuration, database behavior, Last.fm loading, Spotify enrichment, report generation, week-over-week comparison, email sending, Spotify setup and the main automation workflow. The optional playlist error was handled correctly, which demonstrates reliability and error handling.
