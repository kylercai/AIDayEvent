from PIL import Image, ImageTk
import tkinter as tk

#提示用户在终端输入，输入的内容是一个字符串，返回输入的字符串
def get_input():
    print(">>>:")
    return input()

def show_image(image_path: str):
    global photo
    popup = tk.Toplevel()
    popup.title("Image")

    image = Image.open(str)
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(popup, image=photo)
    label.pack()

def popup_show_image(image_path: str):
    root = tk.Tk()
    root.title("Assistant")

    # 创建一个按钮，点击按钮后调用show_image函数
    # button = tk.Button(root, text="Show Image", command=show_image)
    # button.pack()
    show_image(str)

    root.mainloop()
