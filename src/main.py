import customtkinter as ctk
import tkintermapview

class MapViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Heatmap Area Selector")
        self.geometry("1200x800")

        # Create main layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create sidebar frame
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)  # Make row 8 expandable

        # Add controls to sidebar
        self.title_label = ctk.CTkLabel(self.sidebar, text="Map Controls", font=ctk.CTkFont(size=16, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=10, pady=(10, 20))



        # Resolution Selector
        self.resolution_label = ctk.CTkLabel(self.sidebar, text="Resolution:")
        self.resolution_label.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.resolution_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.resolution_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.width_var = ctk.StringVar()
        self.width_entry = ctk.CTkEntry(
            self.resolution_frame, 
            placeholder_text="Width", 
            textvariable=self.width_var,
            validate="key",
            validatecommand=(self.register(self.validate_number), '%P'))
        self.width_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        

        # Add 'X' symbol between width and height
        self.x_symbol = ctk.CTkLabel(self.resolution_frame, text="×")
        self.x_symbol.grid(row=0, column=1, padx=2)

        self.height_var = ctk.StringVar()
        self.height_entry = ctk.CTkEntry(
            self.resolution_frame, 
            placeholder_text="Height", 
            textvariable=self.height_var,
            validate="key",
            validatecommand=(self.register(self.validate_number), '%P'))
        self.height_entry.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        # Configure columns to center the symbol
        self.resolution_frame.columnconfigure(0, weight=1)  # Width entry
        self.resolution_frame.columnconfigure(1, weight=0)  # Symbol (fixed width)
        self.resolution_frame.columnconfigure(2, weight=1)  # Height entry




        # Aspect Ratio Selector
        self.aspect_ratio_label = ctk.CTkLabel(self.sidebar, text="Aspect Ratio:")
        self.aspect_ratio_label.grid(row=3, column=0, padx=10, pady=(10, 0), sticky="w")
        
        # In the ratio_frame section:
        self.ratio_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.ratio_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.ratio_width_var = ctk.StringVar()
        self.ratio_width_entry = ctk.CTkEntry(
            self.ratio_frame, 
            placeholder_text="Width", 
            textvariable=self.ratio_width_var,
            validate="key",
            validatecommand=(self.register(self.validate_number), '%P'))

        self.ratio_width_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        # Add colon between ratio inputs
        self.colon_symbol = ctk.CTkLabel(self.ratio_frame, text=":")
        self.colon_symbol.grid(row=0, column=1, padx=2)
        
        self.ratio_height_var = ctk.StringVar()
        self.ratio_height_entry = ctk.CTkEntry(
            self.ratio_frame, 
            placeholder_text="Height", 
            textvariable=self.ratio_height_var,
            validate="key",
            validatecommand=(self.register(self.validate_number), '%P'))

        self.ratio_height_entry.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        # Configure columns for ratio inputs
        self.ratio_frame.columnconfigure(0, weight=1)  # Ratio width
        self.ratio_frame.columnconfigure(1, weight=0)  # Colon symbol
        self.ratio_frame.columnconfigure(2, weight=1)  # Ratio height

        self.generate_button = ctk.CTkButton(self.sidebar, text="Generate", command=self.on_generate)
        self.generate_button.grid(row=7, column=0, padx=10, pady=10, sticky="sew")

        # Create map frame
        self.map_frame = ctk.CTkFrame(self)
        self.map_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.map_frame.grid_rowconfigure(0, weight=1)
        self.map_frame.grid_columnconfigure(0, weight=1)

        # Create map widget
        self.map_widget = tkintermapview.TkinterMapView(self.map_frame)
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        
                # Create transparent overlay frames
        self.setup_overlay_frames()


        # Set initial values
        self.width_var.set("1920")
        self.height_var.set("1080")
        self.ratio_width_var.set("16")
        self.ratio_height_var.set("9")


        # Set initial map position (London)
        self.map_widget.set_position(59.3882686, 13.4940903)
        self.map_widget.set_zoom(12)

        # Bind change events
        self.width_var.trace_add('write', self.on_resolution_change)
        self.height_var.trace_add('write', self.on_resolution_change)
        self.ratio_width_var.trace_add('write', self.on_aspect_ratio_change)
        self.ratio_height_var.trace_add('write', self.on_aspect_ratio_change)

        # Bind map events
        self.map_widget.add_right_click_menu_command("Print Location",
                                                    command=self.print_location,
                                                    pass_coords=True)

    def validate_number(self, value):
        """Validate that input contains only digits"""
        return value.isdigit() and len(list(value)) <= 6 or value == ""


    def on_zoom_change(self, value):
        """Handle zoom slider changes"""
        self.map_widget.set_zoom(int(value))

    def print_location(self, coords):
        """Print clicked location coordinates"""
        print(f"Clicked location: {coords}")

    def on_generate(self):
        """Handle generate button click"""
        print("Generate button clicked!")
        print(f"Resolution: {self.width_var.get()}x{self.height_var.get()}")
        print(f"Aspect Ratio: {self.ratio_width_var.get()}:{self.ratio_height_var.get()}")

    def on_resolution_change(self, *args):
        """Handle resolution changes"""
        width = self.width_var.get()
        height = self.height_var.get()
        if width and height:
            print(f"Resolution changed to: {width}x{height}")
            # Add your resolution handling logic here

            
    def get_visible_region(self):
            """Get the coordinates of the visible region in the clear square"""
            # Get the position of the clear square in canvas coordinates
            x = self.border_frame.winfo_x() + self.map_frame.winfo_x()
            y = self.border_frame.winfo_y() + self.map_frame.winfo_y()
            
            # Get map coordinates for the clear square corners
            nw = self.map_widget.convert_canvas_coords_to_decimal_coords(
                x, 
                y
            )
            se = self.map_widget.convert_canvas_coords_to_decimal_coords(
                x + self.clear_square_size, 
                y + self.clear_square_size
            )
            
            return nw, se

    def setup_overlay_frames(self):
        """Setup the overlay using CTkFrames"""
        # Size of the clear square in the middle
        self.clear_square_size = 400
        
        # Create four semi-transparent frames for the overlay
        # Top overlay
        self.top_overlay = ctk.CTkFrame(self.map_frame, fg_color=("gray75", "gray25"))
        self.top_overlay.grid(row=0, column=0, sticky="ew")
        
        # Bottom overlay
        self.bottom_overlay = ctk.CTkFrame(self.map_frame, fg_color=("gray75", "gray25"))
        self.bottom_overlay.grid(row=2, column=0, sticky="ew")
        
        # Left overlay
        self.left_overlay = ctk.CTkFrame(self.map_frame, fg_color=("gray75", "gray25"))
        self.left_overlay.grid(row=1, column=0, sticky="ns")
        
        # Right overlay
        self.right_overlay = ctk.CTkFrame(self.map_frame, fg_color=("gray75", "gray25"))
        self.right_overlay.grid(row=1, column=2, sticky="ns")

        # Border frame for the clear area
        self.border_frame = ctk.CTkFrame(self.map_frame, fg_color="transparent", border_color="white", border_width=2)
        self.border_frame.grid(row=1, column=1)

        # Set the size of the clear square
        self.border_frame.configure(width=self.clear_square_size, height=self.clear_square_size)
        
        # Make sure frames stay on top
        for frame in [self.top_overlay, self.bottom_overlay, self.left_overlay, self.right_overlay, self.border_frame]:
            frame.tkraise()

        # Configure grid
        self.map_frame.grid_rowconfigure(1, minsize=self.clear_square_size)
        self.map_frame.grid_columnconfigure(1, minsize=self.clear_square_size)


    def on_aspect_ratio_change(self, *args):
        """Handle resolution changes"""
        width = self.width_var.get()
        height = self.height_var.get()
        if width and height:
            print(f"Aspect-ratio changed to: {width}:{height}")
            # Add your resolution handling logic here

    
if __name__ == "__main__":
    app = MapViewer()
    app.mainloop()