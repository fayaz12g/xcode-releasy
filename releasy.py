import os
import re
import subprocess
import customtkinter as ctk
from tkinter import filedialog
import requests
import json
from datetime import datetime

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BuildApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Xcode Releasy")
        self.geometry("900x700")
        
        # Variables
        self.project_path = ctk.StringVar()
        self.app_name = ctk.StringVar()
        self.project_workspace = ctk.StringVar()
        self.xcode_path = ctk.StringVar(value="Applications/Xcode.app")
        self.output_folder = ctk.StringVar()
        self.upload_to_github = ctk.BooleanVar(value=False)
        self.repo_url = ctk.StringVar(value="username/repository")
        self.api_key = ctk.StringVar()
        self.changelog = ctk.StringVar()
        
        self.create_widgets()
        
    def create_widgets(self):
        # App Name
        ctk.CTkLabel(self, text="App Name (should be the same as your target):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.app_name, width=400).grid(row=0, column=1, padx=5, pady=5)
    
        # Project Selection
        ctk.CTkLabel(self, text="Xcode Project (.xcodeproj):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.project_path, width=400).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(self, text="Browse", command=self.browse_project).grid(row=1, column=2, padx=5, pady=5)
        
        # Xcode Version Selection
        ctk.CTkLabel(self, text="Xcode Version (add '-beta' to use Xcode-beta):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.xcode_path, width=400).grid(row=2, column=1, padx=5, pady=5)
        ctk.CTkButton(self, text="Select", command=self.select_xcode).grid(row=2, column=2, padx=5, pady=5)
        
        # Output Folder
        ctk.CTkLabel(self, text="Output Folder (where the built IPA will go):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.output_folder, width=400).grid(row=3, column=1, padx=5, pady=5)
        ctk.CTkButton(self, text="Browse", command=self.browse_output).grid(row=3, column=2, padx=5, pady=5)
        
        # GitHub Options
        ctk.CTkCheckBox(self, text="Upload to GitHub", variable=self.upload_to_github).grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(self, text="Repository URL:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.repo_url, width=300).grid(row=5, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self, text="API Key:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.api_key, show="*", width=300).grid(row=6, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(self, text="Changelog:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(self, textvariable=self.changelog, width=300).grid(row=7, column=1, padx=5, pady=5, sticky="w")
        
        # Log Output
        self.log_text = ctk.CTkTextbox(self, width=700, height=300)
        self.log_text.grid(row=8, column=0, columnspan=3, padx=10, pady=10)
        
        # Start Button
        ctk.CTkButton(self, text="Start Build", command=self.start_build).grid(row=9, column=0, columnspan=3, pady=10)
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.update_idletasks()
        
    def browse_project(self):
        try:
            # Different method to support bundles that are technically directories
            self.tk.eval('package require Tk')
            path = self.tk.eval('''
                tk_getOpenFile
            ''').strip()

            if not path:
                return  

            path = path.replace('{', '').replace('}', '')
            path = os.path.normpath(path)
            workspace = os.path.join(path, "project.xcworkspace")        

            # Validate Xcode project
            pbxproj = os.path.join(path, "project.pbxproj")
            if not os.path.isfile(pbxproj):
                self.log("Error: Not a valid Xcode project (missing project.pbxproj)")
                return
            
            self.project_path.set(path)
            self.project_workspace.set(workspace)

        except Exception as e:
            self.log(f"Selection error: {str(e)}")

    def select_xcode(self):
        # Different method to support bundles that are technically directories
        self.tk.eval('package require Tk')
        path = self.tk.eval('''
            tk_getOpenFile
        ''').strip()

        if not path:
            return  

        path = path.replace('{', '').replace('}', '')
        path = os.path.normpath(path)
       
        if "Xcode.app" in path or "Xcode-beta.app" in path:
            self.xcode_path.set(path)
        else:
            print("Not a valid Xcode install")
            
    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_folder.set(path)
            
    def get_xcode_developer_dir(self):
        return os.path.join(self.xcode_path.get(), "Contents", "Developer")
    
    def parse_project_versions(self, pbxproj_path):
        with open(pbxproj_path, "r") as f:
            content = f.read()
            
        marketing_version = re.search(r'MARKETING_VERSION = ([\d.]+);', content)
        build_number = re.search(r'CURRENT_PROJECT_VERSION = (\d+);', content)
        
        if not marketing_version or not build_number:
            raise ValueError("Could not find version numbers in project file")
            
        return marketing_version.group(1), int(build_number.group(1))
    
    def update_build_number(self, pbxproj_path, new_build_number):
        with open(pbxproj_path, "r") as f:
            content = f.read()
            
        updated = re.sub(
            r'(CURRENT_PROJECT_VERSION = )(\d+)(;)',
            fr'\g<1>{new_build_number}\3',
            content
        )
        
        with open(pbxproj_path, "w") as f:
            f.write(updated)
            
    def create_ipa(self, app_path, ipa_path):
        payload_dir = os.path.join(os.path.dirname(ipa_path), "Payload")
        os.makedirs(payload_dir, exist_ok=True)
        
        # Copy .app to Payload
        subprocess.run(["cp", "-R", app_path, payload_dir], check=True)
        
        # Zip Payload
        cwd = os.path.dirname(ipa_path)
        ipa_name = os.path.basename(ipa_path)
        subprocess.run(
            ["zip", "-qr", ipa_name, "Payload"],
            cwd=cwd,
            check=True
        )
        
    def create_github_release(self, version, build_number, ipa_path, changelog):
        repo = self.repo_url.get()
        url = f"https://api.github.com/repos/{repo}/releases"
        
        headers = {
            "Authorization": f"token {self.api_key.get()}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "tag_name": f"build-{build_number}",
            "name": f"Version {version} ({build_number})",
            "body": changelog,
            "draft": False,
            "prerelease": False
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        
        upload_url = response.json()["upload_url"].split("{")[0]
        with open(ipa_path, "rb") as f:
            files = {"asset": (os.path.basename(ipa_path), f, "application/octet-stream")}
            upload_response = requests.post(
                f"{upload_url}?name={os.path.basename(ipa_path)}",
                headers=headers,
                files=files
            )
            
        upload_response.raise_for_status()
        
    def start_build(self):
        try:
            # Validate inputs
            if not all([self.project_path.get(), self.xcode_path.get(), self.output_folder.get()]):
                raise ValueError("All required fields must be filled")
                
            # Get project info
            project_dir = os.path.dirname(self.project_path.get())
            pbxproj_path = os.path.join(self.project_path.get(), "project.pbxproj")
            
            # Parse versions
            marketing_version, build_number = self.parse_project_versions(pbxproj_path)
            new_build_number = build_number + 1
            self.log(f"Current version: {marketing_version} ({build_number})")
            self.log(f"New build number: {new_build_number}")
            
            # Update build number
            self.update_build_number(pbxproj_path, new_build_number)
            self.log("Updated project build number")
            
            # Build parameters
            developer_dir = self.get_xcode_developer_dir()
            build_dir = os.path.join(self.output_folder.get(), "Build")
            archive_path = os.path.join(build_dir, f"{self.app_name.get()}.xcarchive")
            app_path = os.path.join(archive_path, "Products", "Applications", f"{self.app_name.get()}.app")
            ipa_path = os.path.join(build_dir, f"{self.app_name.get()}-{marketing_version}-{new_build_number}.ipa")
            
            # Build commands
            env = os.environ.copy()
            env["DEVELOPER_DIR"] = developer_dir
            
            self.log("Starting build...")
            subprocess.run([
                "xcodebuild",
                "-allowProvisioningUpdates",
                "-workspace", self.project_workspace.get(),
                "-scheme", f"{self.app_name.get()}",
                "-sdk", "iphoneos",
                "-configuration", "Release",
                "archive",
                "-archivePath", archive_path
            ], env=env, check=True)
            
            # Create IPA
            self.log("Creating IPA...")
            self.create_ipa(app_path, ipa_path)
            self.log(f"IPA created at {ipa_path}")
            
            # GitHub Upload
            if self.upload_to_github.get():
                self.log("Uploading to GitHub...")
                self.create_github_release(marketing_version, new_build_number, ipa_path, self.changelog.get())
                self.log("GitHub upload complete")
            
            self.log("Build successful!")
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            
if __name__ == "__main__":
    app = BuildApp()
    app.mainloop()