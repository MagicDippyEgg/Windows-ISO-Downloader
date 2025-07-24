import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import urllib.request
import json
import os
import math

# URL for the Windows versions JSON file
WINDOWS_VERSIONS_URL = "https://magicdippyegg.github.io/Windows-ISO-Downloader/windows_versions.json"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Windows ISO Downloader")
        self.geometry("900x600")
        self.style = ttk.Style(self)
        self.style.configure('Treeview', rowheight=24)

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        self.load_progress = ttk.Progressbar(self, mode='indeterminate')
        self.load_progress.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)

        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=(0, 10))
        search_frame.columnconfigure(0, weight=1)
        search_frame.columnconfigure(1, weight=0)

        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        self.search_entry.bind("<Return>", self.perform_search_event)

        self.search_button = ttk.Button(search_frame, text="Search", command=self.search_versions)
        self.search_button.grid(row=0, column=1, sticky='e')

        list_frame = ttk.Frame(self)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        cols = ("Version",)
        self.vers_list = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode='browse')
        for col in cols:
            self.vers_list.heading(col, text=col)
            self.vers_list.column(col, anchor="w", width=200)
        self.vers_list.grid(row=0, column=0, sticky="nsew")
        self.vers_list.bind("<<TreeviewSelect>>", self.on_select)

        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.vers_list.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.vers_list.configure(yscrollcommand=list_scroll.set)

        detail_frame = ttk.Frame(self, padding=(10,10))
        detail_frame.grid(row=2, column=1, sticky="nsew")
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        self.details = ScrolledText(detail_frame, wrap=tk.WORD, height=15)
        self.details.grid(row=0, column=0, sticky="nsew")
        self.details.configure(state=tk.DISABLED)

        self.download_progress = ttk.Progressbar(detail_frame, mode='determinate', maximum=100)
        self.download_progress.grid(row=1, column=0, sticky='ew', pady=(5,10))
        self.download_progress.grid_remove()

        btn_frame = ttk.Frame(detail_frame)
        btn_frame.grid(row=2, column=0, pady=(0,10), sticky="ew")
        btn_frame.columnconfigure(0, weight=1)

        self.download_iso_btn = ttk.Button(
            btn_frame, text="Download ISO", command=self.download_iso, state=tk.DISABLED)
        self.download_iso_btn.grid(row=0, column=0, sticky="ew")

        self.all_versions = []
        self.current_display_versions = []
        self.selected_download_url = None
        self.current_selection_id = None

        threading.Thread(target=self.load_versions, daemon=True).start()

    def load_versions(self):
        """Loads Windows versions from the specified JSON URL."""
        try:
            self.load_progress.start(10)
            resp = urllib.request.urlopen(WINDOWS_VERSIONS_URL)
            data = json.load(resp)
            self.all_versions = data.get("versions", [])
            self.update_version_list(self.all_versions)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Windows versions:\n{e}")
        finally:
            self.load_progress.stop()
            self.load_progress.grid_remove()

    def update_version_list(self, versions_to_display):
        """Clears and repopulates the Treeview with the given list of versions."""
        for item in self.vers_list.get_children():
            self.vers_list.delete(item)
        self.current_display_versions = versions_to_display
        for idx, v in enumerate(self.current_display_versions):
            self.vers_list.insert("", "end", iid=str(idx), values=(v.get("version", "N/A"),))

    def perform_search_event(self, event):
        self.search_versions()

    def search_versions(self):
        """Filters the version list based on the search term."""
        search_term = self.search_entry.get().strip().lower()
        if not search_term:
            self.update_version_list(self.all_versions)
        else:
            filtered_versions = [
                v for v in self.all_versions
                if search_term in v.get("version", "").lower()
            ]
            self.update_version_list(filtered_versions)

        self.show_details("")
        self.download_iso_btn.config(state=tk.DISABLED)
        self.selected_download_url = None
        self.current_selection_id = None

    def on_select(self, ev):
        """Handles selection of a version from the list."""
        sel = self.vers_list.selection()
        if not sel:
            self.show_details("")
            self.download_iso_btn.config(state=tk.DISABLED)
            self.selected_download_url = None
            self.current_selection_id = None
            return

        selected_iid = sel[0]
        self.current_selection_id = selected_iid

        idx = int(selected_iid)
        if idx >= len(self.current_display_versions):
            return

        v = self.current_display_versions[idx]
        self.selected_download_url = v.get("download_url")
        version_name = v.get("version", "N/A")
        selected_notes = v.get("notes", "No additional notes.")

        initial_lines = [
            f"Version: {version_name}",
            f"Download URL: {self.selected_download_url if self.selected_download_url else 'N/A'}",
            f"File Size: Fetching file size...",
            f"Notes: {selected_notes}"
        ]
        self.show_details("\n".join(initial_lines))
        self.download_iso_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._fetch_and_display_file_size,
                         args=(self.selected_download_url, version_name, selected_notes, selected_iid),
                         daemon=True).start()

    def _fetch_and_display_file_size(self, url, version_name, notes, selection_id_at_call):
        """Fetches the file size and updates the details panel."""
        size_str = "N/A"
        can_download = False
        try:
            size_bytes = self._get_file_size(url)
            if size_bytes is not None:
                size_str = self._format_bytes(size_bytes)
                can_download = True
            else:
                size_str = "Could not determine file size (URL might be invalid or unreachable)."
        except Exception as e:
            print(f"Error fetching size for {url}: {e}")
            size_str = f"Error fetching size: {e}"

        self.after(0, self._update_details_with_size, version_name, url, size_str, notes, can_download, selection_id_at_call)

    def _update_details_with_size(self, version_name, url, size_str, notes, can_download, selection_id_at_call):
        """Updates the details text area with file size and re-enables/disables button."""
        if self.current_selection_id != selection_id_at_call:
            return

        lines = [
            f"Version: {version_name}",
            f"Download URL: {url if url else 'N/A'}",
            f"File Size: {size_str}",
            f"Notes: {notes}"
        ]
        self.show_details("\n".join(lines))
        self.download_iso_btn.config(state=tk.NORMAL if self.selected_download_url and can_download else tk.DISABLED)


    def _get_file_size(self, url):
        """Attempts to get the Content-Length of a URL using a HEAD request."""
        if not url:
            return None
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as response:
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

        self.download_progress.grid()
        self.download_progress['value'] = 0
        # Disable all action buttons and the version list during download
        self.download_iso_btn.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.search_entry.config(state=tk.DISABLED)
        self.vers_list.config(selectmode='none') # Disable selection on Treeview

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
            self.download_progress.grid_remove()
            # Re-enable the version list and other controls
            self.vers_list.config(selectmode='browse') # Re-enable selection on Treeview
            self.search_button.config(state=tk.NORMAL)
            self.search_entry.config(state=tk.NORMAL)

            # Restore download button based on current selection
            sel = self.vers_list.selection()
            if sel:
                self.on_select(None) # Re-trigger on_select to refresh button state
            else:
                self.download_iso_btn.config(state=tk.DISABLED)


if __name__ == "__main__":
    App().mainloop()