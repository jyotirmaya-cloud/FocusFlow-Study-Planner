from app import App


def main():
    # On Windows, tell the taskbar this is its own app so it shows our icon
    # instead of grouping it under python.exe
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "focusflow.studyplanner"
        )
    except Exception:
        pass

    App().mainloop()


if __name__ == "__main__":
    main()
