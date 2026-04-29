import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import os

# ==========================================
# 1. FILE CONFIGURATION
# ==========================================
STAMP_IMG = "my_stamp.png"               # Your stamp image file
SIG_IMG = "my_signature.png"             # Your signature image file
FONT_FILE = "handwriting.ttf"            # Your custom handwriting font file (.ttf)
OUTPUT_DIR = "output_pdfs"               # Folder to save the finished files

# Image size settings (Width, Height in PDF points)
STAMP_SIZE = (150, 100) 
SIG_SIZE = (150, 50)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def make_transparent(image_path):
    """Automatically converts white backgrounds to transparent."""
    try:
        img = Image.open(image_path).convert("RGBA")
        data = img.getdata()
        
        new_data = []
        for item in data:
            # If the pixel is mostly white (R>220, G>220, B>220), make it invisible
            if item[0] > 220 and item[1] > 220 and item[2] > 220:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
                
        img.putdata(new_data)
        
        # Save to a temporary memory buffer so PyMuPDF can use it
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        print(f"Error processing image transparency for {image_path}: {e}")
        # Fallback to returning the original file path if something goes wrong
        return open(image_path, "rb").read()

# ==========================================
# 3. MAIN APPLICATION CLASS
# ==========================================
class PDFStamperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YASHASVI ASSOCIATE - Pro Drag & Drop Stamper")
        
        # Ensure output directory exists
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        # 1. Select PDF using File Browser
        self.input_pdf_path = filedialog.askopenfilename(
            title="Select the blank PDF to sign",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not self.input_pdf_path:
            root.destroy()
            return

        filename = os.path.basename(self.input_pdf_path)
        self.output_pdf_path = os.path.join(OUTPUT_DIR, f"signed_{filename}")

        # 2. Load PDF into memory as raw bytes to generate clean previews
        try:
            with open(self.input_pdf_path, "rb") as f:
                self.original_pdf_bytes = f.read()
            self.doc = fitz.open("pdf", self.original_pdf_bytes)
            self.page = self.doc[0] 
        except Exception as e:
            messagebox.showerror("Error", f"Could not load PDF: {e}")
            root.destroy()
            return

        self._drag_data = {"x": 0, "y": 0, "item": None}
        self.date_str = ""
        self.preview_doc = None # Will hold the stamped version during preview

        self.setup_ui()
        self.root.after(100, self.ask_for_date)

    def setup_ui(self):
        # Instruction Bar
        self.info_label = tk.Label(self.root, text="EDIT MODE: Drag the elements into position, then click Preview.", font=("Arial", 12, "bold"), bg="yellow")
        self.info_label.pack(fill=tk.X, pady=5)

        # Action Buttons
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(fill=tk.X, pady=5)
        
        # Save Button (Disabled until Preview is generated)
        self.btn_save = tk.Button(self.btn_frame, text="2. Confirm & Save", command=self.save_pdf, state=tk.DISABLED, bg="green", fg="white", font=("Arial", 10, "bold"))
        self.btn_save.pack(side=tk.RIGHT, padx=10)

        # Edit Button (Hidden initially)
        self.btn_edit = tk.Button(self.btn_frame, text="Back to Editing", command=self.back_to_editing, state=tk.DISABLED, font=("Arial", 10))
        self.btn_edit.pack(side=tk.RIGHT, padx=10)

        # Preview Button
        self.btn_preview = tk.Button(self.btn_frame, text="1. Preview Document", command=self.generate_preview, state=tk.DISABLED, bg="#0078D7", fg="white", font=("Arial", 10, "bold"))
        self.btn_preview.pack(side=tk.RIGHT, padx=10)

        # PDF Canvas Area
        pix = self.page.get_pixmap(matrix=fitz.Matrix(1, 1))
        img_data = io.BytesIO(pix.tobytes("png"))
        self.pil_image = Image.open(img_data)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.vbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.hbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(self.canvas_frame, width=800, height=800, 
                                xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vbar.config(command=self.canvas.yview)
        self.hbar.config(command=self.canvas.xview)
        
        # Add background image to canvas (Save ID to swap during preview)
        self.bg_image_id = self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        
        # Drag bindings
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)

    def ask_for_date(self):
        self.date_str = simpledialog.askstring("Input Date", "Enter the date to print on the document:")
        if not self.date_str:
            self.date_str = "DD-MM-YYYY" 
        
        self.spawn_draggable_elements()
        self.btn_preview.config(state=tk.NORMAL)

    def spawn_draggable_elements(self):
        self.date_id = self.canvas.create_text(100, 100, text=self.date_str, fill="blue", font=("Arial", 16, "bold"), anchor="sw", tags=("draggable", "date_group"))
        self.stamp_rect = self.canvas.create_rectangle(100, 150, 100 + STAMP_SIZE[0], 150 + STAMP_SIZE[1], outline="red", width=3, tags=("draggable", "stamp_group"))
        self.stamp_text = self.canvas.create_text(105, 155, text="[STAMP]\nDrag Me", fill="red", font=("Arial", 12, "bold"), anchor="nw", tags=("draggable", "stamp_group"))
        self.sig_rect = self.canvas.create_rectangle(100, 300, 100 + SIG_SIZE[0], 300 + SIG_SIZE[1], outline="green", width=3, tags=("draggable", "sig_group"))
        self.sig_text = self.canvas.create_text(105, 305, text="[SIGNATURE]\nDrag Me", fill="green", font=("Arial", 12, "bold"), anchor="nw", tags=("draggable", "sig_group"))

    def on_drag_start(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        closest_items = self.canvas.find_closest(x, y)
        if not closest_items: return
        tags = self.canvas.gettags(closest_items[0])
        if "draggable" in tags:
            for tag in ["date_group", "stamp_group", "sig_group"]:
                if tag in tags:
                    self._drag_data["item"] = tag
                    self._drag_data["x"], self._drag_data["y"] = x, y
                    break

    def on_drag_motion(self, event):
        if self._drag_data["item"] is None: return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        dx, dy = x - self._drag_data["x"], y - self._drag_data["y"]
        self.canvas.move(self._drag_data["item"], dx, dy)
        self._drag_data["x"], self._drag_data["y"] = x, y

    def on_drag_stop(self, event):
        self._drag_data["item"] = None

    def generate_preview(self):
        """Applies stamps to a copy of the PDF and shows the real result."""
        try:
            date_coords = self.canvas.coords(self.date_id)
            stamp_coords = self.canvas.coords(self.stamp_rect)
            sig_coords = self.canvas.coords(self.sig_rect)

            # Open a fresh copy of the document
            self.preview_doc = fitz.open("pdf", self.original_pdf_bytes)
            page = self.preview_doc[0]

            # Convert to PDF coordinates
            date_pt = fitz.Point(date_coords[0], date_coords[1])
            stamp_box = fitz.Rect(stamp_coords[0], stamp_coords[1], stamp_coords[2], stamp_coords[3])
            sig_box = fitz.Rect(sig_coords[0], sig_coords[1], sig_coords[2], sig_coords[3])

            # 1. Insert Date with Blue Pen Color (0, 0.1, 0.8)
            if os.path.exists(FONT_FILE):
                page.insert_font(fontname="hw_font", fontfile=FONT_FILE)
                page.insert_text(date_pt, self.date_str, fontname="hw_font", fontsize=14, color=(0, 0.1, 0.8))
            else:
                page.insert_text(date_pt, self.date_str, fontsize=12, color=(0, 0.1, 0.8))

            # 2. Insert Images with Auto-Transparency
            page.insert_image(stamp_box, stream=make_transparent(STAMP_IMG))
            page.insert_image(sig_box, stream=make_transparent(SIG_IMG))

            # Render the stamped document to an image for preview
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            img_data = io.BytesIO(pix.tobytes("png"))
            self.pil_preview = Image.open(img_data)
            self.tk_preview = ImageTk.PhotoImage(self.pil_preview)

            # Update Canvas to show real preview, hide drag boxes
            self.canvas.itemconfig(self.bg_image_id, image=self.tk_preview)
            self.canvas.itemconfigure("draggable", state="hidden")

            # Update UI state
            self.info_label.config(text="PREVIEW MODE: This is exactly how the final PDF will look.", bg="orange")
            self.btn_preview.config(state=tk.DISABLED)
            self.btn_edit.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview:\n{e}")

    def back_to_editing(self):
        """Restores the blank PDF and un-hides the draggable boxes."""
        self.canvas.itemconfig(self.bg_image_id, image=self.tk_image)
        self.canvas.itemconfigure("draggable", state="normal")
        
        self.info_label.config(text="EDIT MODE: Drag the elements into position, then click Preview.", bg="yellow")
        self.btn_preview.config(state=tk.NORMAL)
        self.btn_edit.config(state=tk.DISABLED)
        self.btn_save.config(state=tk.DISABLED)

    def save_pdf(self):
        """Saves the preview document to the hard drive."""
        try:
            if self.preview_doc:
                self.preview_doc.save(self.output_pdf_path)
                messagebox.showinfo("Success", f"Document saved successfully to:\n{self.output_pdf_path}")
                self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    
    # Hide the main window temporarily while the file dialog is open
    root.withdraw() 
    app = PDFStamperApp(root)
    
    # Show the main window again once the file is selected
    if getattr(app, 'input_pdf_path', None): 
        root.deiconify()
        root.geometry("1000x800")
        root.mainloop()