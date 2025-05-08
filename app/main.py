import grpc
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import numpy as np
from queue import PriorityQueue
import random
import grpc
import graph_pb2 as service_pb2
import graph_pb2_grpc as service_pb2_grpc
import argparse

class MazeSolverApp:
    def __init__(self, root, stub):
        self.root = root
        self.stub = stub
        self.root.title("Maze Solver with Grid Snapping")
        
        # labyrinth parameters
        self.cell_size = 10
        self.maze_width = 1000
        self.maze_height = 1000
        
        self.start_point = None
        self.end_point = None
        self.image = None
        self.tk_image = None
        self.maze_array = None
        
        self.create_maze_from_matrix()
        
        # interface creation
        self.create_widgets()
        
    def create_maze_from_matrix(self):
        maze_matrix = []

        filename = "matrix.txt"
        with open(filename, 'r') as file:
            for line in file:
                row = [int(num) for num in line.strip().split()]
                maze_matrix.append(row)

    
        
        self.maze_array = np.array(maze_matrix)
        
        # labyrinth image
        img_width = self.maze_width * self.cell_size
        img_height = self.maze_height * self.cell_size
        self.image = Image.new('RGB', (img_width, img_height), color='#b0bcbf')
        draw = ImageDraw.Draw(self.image)
        
        # draw walls
        for y in range(self.maze_height):
            for x in range(self.maze_width):
                if self.maze_array[y, x] == 0:
                    draw.rectangle([
                        x * self.cell_size,
                        y * self.cell_size,
                        (x + 1) * self.cell_size - 1,
                        (y + 1) * self.cell_size - 1
                    ], fill='#080808')
        
        # draw grid
        for x in range(0, img_width, self.cell_size):
            draw.line([(x, 0), (x, img_height)], fill=10)
        for y in range(0, img_height, self.cell_size):
            draw.line([(0, y), (img_width, y)], fill=10)
        
        self.tk_image = ImageTk.PhotoImage(self.image)
        
        self.maze_array = np.kron(self.maze_array, np.ones((self.cell_size, self.cell_size), dtype=int))
    
    def create_widgets(self):
        self.reset_btn = tk.Button(self.root, text="Reset", command=self.reset)
        self.reset_btn.pack(pady=5)

        self.solve_btn = tk.Button(self.root, text="Solve Maze", command=self.solve_maze)
        self.solve_btn.pack(pady=5)

        # container for canvas and scrollbars
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        # vertical scrollbar
        v_scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # horyzontal scrollbar
        h_scrollbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        canvas_width = self.maze_width * self.cell_size
        canvas_height = self.maze_height * self.cell_size
        self.canvas = tk.Canvas(
            frame,
            width=canvas_width,
            height=canvas_height,
            bg='white',
            scrollregion=(0, 0, canvas_width, canvas_height),
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.bind("<Button-1>", self.set_points)

        self.status = tk.Label(self.root, text="Select start and end points in the maze", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X)
    
    def set_points(self, event):
        abs_x = self.canvas.canvasx(event.x)
        abs_y = self.canvas.canvasy(event.y)

        cell_x = int(abs_x) // self.cell_size
        cell_y = int(abs_y) // self.cell_size

        if (0 <= cell_x < self.maze_width and 
            0 <= cell_y < self.maze_height and 
            self.maze_array[cell_y * self.cell_size, cell_x * self.cell_size] == 1):

            center_x = cell_x * self.cell_size + self.cell_size // 2
            center_y = cell_y * self.cell_size + self.cell_size // 2

            if self.start_point is None:
                self.start_point = (center_y, center_x)
                self.draw_point(center_x, center_y, 'green')
                self.status.config(text=f"Start set at ({cell_x}, {cell_y}). Click to set end point")
            elif self.end_point is None:
                self.end_point = (center_y, center_x)
                self.draw_point(center_x, center_y, 'red')
                self.status.config(text=f"End set at ({cell_x}, {cell_y}). Click 'Solve Maze' to find path")
    
    def draw_point(self, x, y, color):
        radius = self.cell_size // 3
        self.canvas.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color, outline=color
        )
    
    def reset(self):
        self.start_point = None
        self.end_point = None
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.status.config(text="Select start and end points in the maze")
    
    def solve_maze(self):
        if self.start_point is None or self.end_point is None:
            self.status.config(text="Please set both start and end points")
            return
            
        try:
            path = self.a_star_search()
            if path:
                self.draw_path(path, color='#1565C0')
                self.status.config(text="Path found!")
            else:
                self.status.config(text="No path found!")
        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")
    
    def a_star_search(self):
        # need to divide by cell size to get normal coordinates
        request = service_pb2.PathRequest(
                start=service_pb2.Point(x=int(self.start_point[0]//self.cell_size), y=int(self.start_point[1]//self.cell_size)),
                end=service_pb2.Point(x=int(self.end_point[0]//self.cell_size), y=int(self.end_point[1]//self.cell_size))
            )
        response = stub.GetPath(request)
        path = [(p.x, p.y) for p in response.path_points]
        return path
    
    def draw_path(self, path, color='blue'):
        img_with_path = self.image.copy()
        draw = ImageDraw.Draw(img_with_path)
        
        cell_path = []
        for y, x in path:
            cell_x = int(x)
            cell_y = int(y)
            center_x = cell_x * self.cell_size + self.cell_size // 2
            center_y = cell_y * self.cell_size + self.cell_size // 2
            cell_path.append((center_y, center_x))
        
        # path is lines between points
        for i in range(len(cell_path) - 1):
            y1, x1 = cell_path[i]
            y2, x2 = cell_path[i+1]
            draw.line([(x1, y1), (x2, y2)], fill=color, width=5)
        
        radius = self.cell_size // 4
        for y, x in cell_path:
            draw.ellipse([
                x - radius, y - radius,
                x + radius, y + radius
            ], fill=color)
        
        self.tk_image = ImageTk.PhotoImage(img_with_path)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        y, x = self.start_point
        self.draw_point(x, y, 'green')
        y, x = self.end_point
        self.draw_point(x, y, 'red')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=9999, help='Server port')
    args = parser.parse_args()
    host='0.0.0.0'
    port=9999
    channel = grpc.insecure_channel(f'{args.host}:{args.port}')
    stub = service_pb2_grpc.PathServiceStub(channel)
    try:
        print("Testing connection to server...")
        grpc.channel_ready_future(channel).result(timeout=5)
        print("Connected successfully!")
    except grpc.FutureTimeoutError:
        print("Failed to connect to server")
    root = tk.Tk()
    app = MazeSolverApp(root, stub)
    root.mainloop()
