# TODO: GDS Setup Process Development

## Goal
Implement a guided setup process for the Google Drive Shell (GDS) tool to ensure all necessary configurations and credentials are properly set up.

## Task Description
Develop a GUI-based setup interface that is triggered when the user executes `GOOGLE_DRIVE --setup`. This interface will guide the user through the initial configuration steps, including setting up server accounts and other essential information stored in `GOOGLE_DRIVE_DATA`.

## Detailed Setup Steps (To be implemented in GUI)
1. **Workspace Verification**: Ensure the current directory is correctly identified as the project root.
2. **Path Configuration**:
   - `LOCAL_EQUIVALENT`: The local directory synchronized with Google Drive.
   - `REMOTE_ROOT`: The base directory in Google Drive for GDS operations.
3. **API Credentials Setup**:
   - **Service Account**: User provides the JSON key file content or path.
   - **OAuth 2.0**: (Optional) Alternative authentication method.
4. **Environment Check**: Verify Python dependencies and system permissions.
5. **Connectivity Test**: Run a simple `echo` command on the remote side to verify everything is working.

## How to find your Service Account JSON Key:
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Select your project from the top dropdown.
3.  In the left sidebar, navigate to **IAM & Admin** > **Service Accounts**.
4.  Find your service account in the list.
5.  Click on the service account name, then go to the **Keys** tab.
6.  Click **Add Key** > **Create new key**, select **JSON**, and click **Create**.
7.  The JSON file will be downloaded to your computer.

## Key Features
- **Trigger**: New command `GOOGLE_DRIVE --setup`.
- **UI Framework**: Tkinter.
- **Data Persistence**: Save configurations to `GOOGLE_DRIVE_DATA/cache_config.json` and other relevant data files.

## Future Enhancements
- Integration with the main GDS shell for first-time user detection.
- Multi-user/account support within the setup process.


