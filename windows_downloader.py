import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import urllib.request
import json
import os
import math # Import math for size formatting

# URL for the Windows versions JSON file
WINDOWS_VERSIONS_URL = "https://magicdippyegg.github.io/Windows-ISO-Downloader/windows_versions.json"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windows ISO Downloader")
        self.geometry("900x600")
        self.style = ttk.Style(self)
        self.style.configure('Treeview', rowheight=24)

        # Layout: progress at top, then search, then list/details below
        self.rowconfigure(0, weight=0) # For progress bar
        self.rowconfigure(1, weight=0) # For search bar
        self.rowconfigure(2, weight=1) # For main content
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        # Progress bar for loading versions (spans both columns)
        self.load_progress = ttk.Progressbar(self, mode='indeterminate')
        self.load_progress.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)

        # Search bar frame
        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=(0, 10))
        search_frame.columnconfigure(0, weight=1) # Search entry
        search_frame.columnconfigure(1, weight=0) # Search button

        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        self.search_entry.bind("<Return>", self.perform_search_event) # Bind Enter key

        self.search_button = ttk.Button(search_frame, text="Search", command=self.search_versions)
        self.search_button.grid(row=0, column=1, sticky='e')

        # Frame to hold version list and scrollbar
        list_frame = ttk.Frame(self)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Version list on left - only "Version" column now
        cols = ("Version",)
        self.vers_list = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode='browse')
        for col in cols:
            self.vers_list.heading(col, text=col)
            self.vers_list.column(col, anchor="w", width=200)
        self.vers_list.grid(row=0, column=0, sticky="nsew")
        self.vers_list.bind("<<TreeviewSelect>>", self.on_select)

        # Scrollbar for version list
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.vers_list.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.vers_list.configure(yscrollcommand=list_scroll.set)

        # Details panel on right
        detail_frame = ttk.Frame(self, padding=(10,10))
        detail_frame.grid(row=2, column=1, sticky="nsew")
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        # Details text
        self.details = ScrolledText(detail_frame, wrap=tk.WORD, height=15)
        self.details.grid(row=0, column=0, sticky="nsew")
        self.details.configure(state=tk.DISABLED)

        # Download progress bar under details
        self.download_progress = ttk.Progressbar(detail_frame, mode='determinate', maximum=100)
        self.download_progress.grid(row=1, column=0, sticky='ew', pady=(5,10))
        self.download_progress.grid_remove()

        # Buttons
        btn_frame = ttk.Frame(detail_frame)
        btn_frame.grid(row=2, column=0, pady=(0,10), sticky="ew")
        btn_frame.columnconfigure(0, weight=1) # Only one button now

        self.download_iso_btn = ttk.Button(
            btn_frame, text="Download ISO", command=self.download_iso, state=tk.DISABLED)
        self.download_iso_btn.grid(row=0, column=0, sticky="ew")

        self.all_versions = [] # Store the complete list of versions
        self.current_display_versions = [] # Store the currently filtered/displayed versions
        self.selected_download_url = None # To store the URL of the selected ISO

        threading.Thread(target=self.load_versions, daemon=True).start()

    def load_versions(self):
        """Loads Windows versions from the specified JSON URL."""
        try:
            self.load_progress.start(10)
            resp = urllib.request.urlopen(WINDOWS_VERSIONS_URL)
            data = json.load(resp)
            self.all_versions = data.get("versions", []) # Get the list of versions
            self.update_version_list(self.all_versions) # Display all initially
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Windows versions:\n{e}")
        finally:
            self.load_progress.stop()
            self.load_progress.grid_remove()

    def update_version_list(self, versions_to_display):
        """Clears and repopulates the Treeview with the given list of versions."""
        for item in self.vers_list.get_children():
            self.vers_list.delete(item)
        self.current_display_versions = versions_to_display # Update the list of currently displayed versions
        for idx, v in enumerate(self.current_display_versions):
            # Only insert the version name into the Treeview
            self.vers_list.insert("", "end", iid=idx, values=(v.get("version", "N/A"),))

    def perform_search_event(self, event):
        """Called when Enter key is pressed in the search entry."""
        self.search_versions()

    def search_versions(self):
        """Filters the version list based on the search term."""
        search_term = self.search_entry.get().strip().lower()
        if not search_term:
            self.update_version_list(self.all_versions) # Show all if search is empty
            return

        filtered_versions = [
            v for v in self.all_versions
            if search_term in v.get("version", "").lower()
        ]
        self.update_version_list(filtered_versions)
        self.show_details("") # Clear details when search changes
        # Disable button until a new selection is made
        self.download_iso_btn.config(state=tk.DISABLED)

    def on_select(self, ev):
        """Handles selection of a version from the list."""
        sel = self.vers_list.selection()
        if not sel:
            # Clear details and disable button if nothing is selected
            self.show_details("")
            self.download_iso_btn.config(state=tk.DISABLED)
            self.selected_download_url = None
            return

        idx = int(sel[0])
        if idx >= len(self.current_display_versions):
            return # Index out of bounds if selection was made on old list

        v = self.current_display_versions[idx]
        self.selected_download_url = v.get("download_url")

        lines = [
            f"Version: {v.get('version', 'N/A')}",
            f"Download URL: {v.get('download_url', 'N/A')}"
        ]

        self.show_details("\n".join(lines) + "\nFetching file size...")
        self.download_iso_btn.config(state=tk.DISABLED) # Temporarily disable while fetching size
        # Start a thread to fetch file size
        threading.Thread(target=self._fetch_and_display_file_size, args=(self.selected_download_url, v.get('version', 'N/A')), daemon=True).start()


    def _fetch_and_display_file_size(self, url, version_name):
        """Fetches the file size and updates the details panel."""
        size_str = "N/A"
        can_download = False # Flag to control button state
        try:
            size_bytes = self._get_file_size(url)
            if size_bytes is not None:
                size_str = self._format_bytes(size_bytes)
                can_download = True # Only enable if size is successfully fetched
            else:
                size_str = "Could not determine file size (URL might be invalid or unreachable)."
        except Exception as e:
            print(f"Error fetching size for {url}: {e}")
            size_str = f"Error fetching size: {e}"

        # Update the details text and button state on the main thread
        self.after(0, self._update_details_with_size, version_name, url, size_str, can_download)

    def _update_details_with_size(self, version_name, url, size_str, can_download):
        """Updates the details text area with file size and re-enables/disables button."""
        lines = [
            f"Version: {version_name}",
            f"Download URL: {url}",
            f"File Size: {size_str}"
        ]
        self.show_details("\n".join(lines))
        # Re-enable download button based on whether a URL was found AND size was successfully determined
        self.download_iso_btn.config(state=tk.NORMAL if self.selected_download_url and can_download else tk.DISABLED)


    def _get_file_size(self, url):
        """Attempts to get the Content-Length of a URL using a HEAD request."""
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req) as response:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    return int(content_length)
        except Exception as e:
            print(f"Could not get file size for {url}: {e}")
        return None

    def _format_bytes(self, bytes_val):
        """Formats bytes into human-readable string (KB, MB, GB, TB)."""
        if bytes_val is None:
            return "N/A"
        if bytes_val == 0:
            return "0 Bytes"
        size_name = ("Bytes", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(bytes_val, 1024)))
        p = math.pow(1024, i)
        s = round(bytes_val / p, 2)
        return f"{s} {size_name[i]}"

    def show_details(self, text):
        """Updates the details text area."""
        self.details.configure(state=tk.NORMAL)
        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, text)
        self.details.configure(state=tk.DISABLED)

    def download_iso(self):
        """Initiates the ISO download."""
        if not self.selected_download_url:
            messagebox.showwarning("No Selection", "Please select a Windows version to download.")
            return

        default_name = os.path.basename(self.selected_download_url)
        path = filedialog.asksaveasfilename(
            defaultextension=".iso",
            initialfile=default_name,
            filetypes=[("ISO Image", "*.iso"), ("All files","*.*")]
        )
        if not path:
            return

        # Show determinate progress bar
        self.download_progress.grid()
        self.download_progress['value'] = 0
        # Disable all action buttons during download
        self.download_iso_btn.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)

        threading.Thread(target=self._download_thread, args=(self.selected_download_url, path), daemon=True).start()

    def _report_hook(self, block_num, block_size, total_size):
        """Callback for urllib.request.urlretrieve to update download progress."""
        if total_size > 0:
            percent = block_num * block_size * 100 / total_size
            self.download_progress['value'] = min(percent, 100)
            self.update_idletasks()

    def _download_thread(self, url, path):
        """Handles the actual file download in a separate thread."""
        try:
            urllib.request.urlretrieve(url, path, reporthook=self._report_hook)
            messagebox.showinfo("Downloaded", f"Saved to: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Download failed:\n{e}")
        finally:
            # Hide download progress and restore buttons based on current selection
            self.download_progress.grid_remove()
            # Re-enable button based on current selection if any
            sel = self.vers_list.selection()
            if sel:
                # Re-trigger on_select to re-evaluate button state
                self.on_select(None) # Pass None as event as we are not reacting to a real event
            else:
                self.download_iso_btn.config(state=tk.DISABLED)

            self.search_button.config(state=tk.NORMAL)
            self.search_entry.config(state=tk.NORMAL)


if __name__ == "__main__":
    App().mainloop()
