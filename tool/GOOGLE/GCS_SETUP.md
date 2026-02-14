# Google Drive Remote Controller (GCS) Setup Guide

To enable remote file management via Google Drive, you need to set up a Google Cloud Service Account and authorize it to access your Drive folders.

## 1. Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top and select **New Project**.
3. Give it a name (e.g., `My-Drive-Manager`) and click **Create**.

## 2. Enable Google Drive API
1. In the sidebar, go to **APIs & Services** > **Library**.
2. Search for **"Google Drive API"**.
3. Click on it and select **Enable**.

## 3. Create a Service Account
1. In the sidebar, go to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **Service Account**.
3. Enter a name (e.g., `drive-controller`) and click **Create and Continue**.
4. (Optional) Grant the account the **Editor** role, then click **Done**.
5. Copy the **Service Account Email** (e.g., `drive-controller@your-project.iam.gserviceaccount.com`). **Save this for Step 5.**

## 4. Generate JSON Key
1. Click on the newly created Service Account from the list.
2. Go to the **Keys** tab.
3. Click **Add Key** > **Create New Key**.
4. Select **JSON** and click **Create**.
5. A JSON file will be downloaded to your computer. **Keep this file secure!**
6. Save this file to the project's data directory (usually `data/google/console_key.json`).

## 5. Share Your Drive Folder
For the Service Account to "see" your files, you must explicitly share the folder with it:
1. Open [Google Drive](https://drive.google.com/).
2. Right-click the folder you want to manage.
3. Select **Share**.
4. Paste the **Service Account Email** you copied in Step 3.
5. Set the permission to **Editor** (required for `mv`, `rm`, etc.) or **Viewer** (for `ls`, `cat`).
6. Uncheck "Notify people" and click **Share**.

## 6. Verification
Run the following command to test the connection:
```bash
GOOGLE GCS ls --folder-id <YOUR_FOLDER_ID>
```
*Note: The Folder ID is the long string at the end of the folder's URL.*

