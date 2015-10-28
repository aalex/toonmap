#!/usr/bin/env python
from gi.repository import Gtk
from toonloopwizard import cameras

class WizardWindow(Gtk.Window):
    """
    Toonloop wizard window.
    """
    def __init__(self, configuration):
        self.configuration = configuration
        Gtk.Window.__init__(self, title="Toonloop Configuration Wizard")

        box = Gtk.Box(spacing=6)
        self.add(box)

        camera_liststore = Gtk.ListStore(str)
        camera_list = cameras.list_v4l2_cameras()
        for camera in camera_list:
            camera_liststore.append([str(camera)])

        combo1 = Gtk.ComboBox.new_with_model(camera_liststore)
        renderer_text = Gtk.CellRendererText()
        combo1.pack_start(renderer_text, True)
        combo1.add_attribute(renderer_text, "text", 0)
        combo1.connect('changed', self.camera_combo_changed_cb)
        box.add(combo1)

        button1 = Gtk.Button("Choose Project Folder")
        button1.connect("clicked", self.on_folder_clicked)
        box.add(button1)

        button2 = Gtk.Button("Run Toonloop!")
        button2.connect("clicked", self.on_run_clicked)
        box.add(button2)

        self.connect('destroy', self.destroy_cb)

    def destroy_cb(self, window):
        Gtk.main_quit()

    def camera_combo_changed_cb(self, combo):
        print("camera_combo_changed_cb")
        tree_iter = combo.get_active_iter()
        if tree_iter != None:
            model = combo.get_model()
            value = model[tree_iter][0]
            print("Selected: value=%s" % value)
            try:
                video_source = value.split(" ")[0]
                print("Set video-source to %s" % (video_source))
                self.configuration.video_source = video_source
            except KeyError, e:
                print("KeyError while setting video source %s" % (e))


    def on_run_clicked(self, widget):
        print("Running Toonloop!")
        self.destroy()

    def on_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog("Please choose a folder", self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             "Select", Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Select clicked")
            print("Folder selected: " + dialog.get_filename())
            self.configuration.project_home = dialog.get_filename()
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()


def show_window_and_update_config(configuration):
    win = WizardWindow(configuration)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

    return win.configuration

