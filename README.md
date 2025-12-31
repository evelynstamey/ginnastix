# ginnastix

Data-driven gymnastics

## [Prerequisite] Google Sheets Setup

1. Create the `ginnastix` GCP project
2. Enable the API Google Sheets API
3. Configure the OAuth consent screen
4. Authorize credentials for a desktop application
5. Generate client secret and download JSON to `credentials.json`

Ref: https://developers.google.com/workspace/sheets/api/quickstart/python

## Local Setup

1. Install `mise`: https://mise.jdx.dev/getting-started.html#installing-mise-cli
2. Install `uv`: https://docs.astral.sh/uv/getting-started/installation/#installation-methods
3. Run `mise run install`
4. Run `mise run test`
5. Run `mise run format`

## App Authorization

### Generate client secrets

1. Go to https://console.cloud.google.com/auth/clients/236291344840-vdd3f9t32k8svbv3mrfvna1vkil41vt8.apps.googleusercontent.com?project=ginnastix
2. Click "Add secret"
3. Click "Download JSON"
4. Copy downloaded file to `credentials.json`
5. Click "Disable" on old secret (if exists)

### Other notes

- Use the `google_sheets.authenticate` method to manage authorization to the Google Sheets API
- If the **ginnastix** app is in "testing" you will need to create a new client secret every 7 days
- If the **ginnastix** app is in "production" your client secret has a longer life span
- To configure the **ginnastix** app audience, go to: https://console.cloud.google.com/auth/audience?project=ginnastix
- When authorizing the **gynnastix** app in a web browser, you may see the warning "Google hasn’t verified this app"
  - This is because the app is "in production" but not verified
  - To bypass this warning, click "Advanced" >> "Go to ginnastix (unsafe)" >> "Continue"

## Usage

In `pyproject.toml` we configure the script:

```
[project.scripts]
ginnastix-class = "ginnastix_class.entrypoint:cli"
```

### Example usage

```
ginnastix-class attendance
```

```
ginnastix-class skills
```

```
ginnastix-class behavior-report
```
