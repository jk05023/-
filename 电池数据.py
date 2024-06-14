import wx
import os
import shutil
import json
from datetime import datetime
from functools import partial

class FileListItem(wx.Panel):
    def __init__(self, parent, file_info, delete_handler, download_handler, open_handler, open_folder_handler):
        super().__init__(parent)
        self.file_info = file_info
        self.delete_handler = delete_handler
        self.download_handler = download_handler
        self.open_handler = open_handler
        self.open_folder_handler = open_folder_handler

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        self.file_name = wx.StaticText(self, label=file_info['name'])
        self.timestamp = wx.StaticText(self, label=file_info['timestamp'])

        hbox1.Add(self.file_name, proportion=1, flag=wx.ALL, border=5)
        hbox1.Add(self.timestamp, proportion=1, flag=wx.ALL, border=5)

        self.delete_btn = wx.Button(self, label="删除", size=(60, 25))
        self.download_btn = wx.Button(self, label="下载", size=(60, 25))
        self.open_btn = wx.Button(self, label="打开", size=(60, 25))
        self.open_folder_btn = wx.Button(self, label="打开文件夹", size=(80, 25))

        hbox2.Add(self.delete_btn, flag=wx.ALL, border=5)
        hbox2.Add(self.download_btn, flag=wx.ALL, border=5)
        hbox2.Add(self.open_btn, flag=wx.ALL, border=5)
        hbox2.Add(self.open_folder_btn, flag=wx.ALL, border=5)

        vbox.Add(hbox1, flag=wx.EXPAND)
        vbox.Add(hbox2, flag=wx.EXPAND)

        self.SetSizer(vbox)

        self.delete_btn.Bind(wx.EVT_BUTTON, self.OnDelete)
        self.download_btn.Bind(wx.EVT_BUTTON, self.OnDownload)
        self.open_btn.Bind(wx.EVT_BUTTON, self.OnOpen)
        self.open_folder_btn.Bind(wx.EVT_BUTTON, self.OnOpenFolder)

    def OnDelete(self, event):
        self.delete_handler(self.file_info)

    def OnDownload(self, event):
        self.download_handler(self.file_info)

    def OnOpen(self, event):
        self.open_handler(self.file_info)

    def OnOpenFolder(self, event):
        self.open_folder_handler(self.file_info)


class BatteryDataApp(wx.Frame):
    def __init__(self, *args, **kw):
        super(BatteryDataApp, self).__init__(*args, **kw)

        self.directories = {}  # 保存目录和文件信息
        self.current_directory = None
        self.data_file = 'directory_data.json'

        self.InitUI()
        self.LoadDirectoryData()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 上传文件选择器
        self.filePicker = wx.FilePickerCtrl(panel, message="选择文件上传")
        vbox.Add(self.filePicker, flag=wx.EXPAND | wx.ALL, border=10)

        # 创建目录按钮
        create_dir_btn = wx.Button(panel, label='创建目录')
        create_dir_btn.Bind(wx.EVT_BUTTON, self.OnCreateDirectory)
        vbox.Add(create_dir_btn, flag=wx.EXPAND | wx.ALL, border=10)

        # 上传文件按钮
        upload_btn = wx.Button(panel, label='上传文件')
        upload_btn.Bind(wx.EVT_BUTTON, self.OnUploadFile)
        vbox.Add(upload_btn, flag=wx.EXPAND | wx.ALL, border=10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # 目录列表
        self.dirList = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.dirList.InsertColumn(0, '目录', width=200)
        self.dirList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnDirSelected)
        self.dirList.Bind(wx.EVT_RIGHT_DOWN, self.OnRightClick)
        hbox.Add(self.dirList, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        # 文件列表和功能区
        vbox_files = wx.BoxSizer(wx.VERTICAL)

        # 文件搜索框和排序按钮
        search_and_sort_box = wx.BoxSizer(wx.HORIZONTAL)
        self.search_text = wx.TextCtrl(panel)
        self.search_btn = wx.Button(panel, label='搜索')
        self.search_btn.Bind(wx.EVT_BUTTON, self.OnSearchFiles)
        self.sort_btn = wx.Button(panel, label='按时间排序', size=(100, 25))
        self.sort_btn.Bind(wx.EVT_BUTTON, self.OnSortFiles)
        search_and_sort_box.Add(self.search_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        search_and_sort_box.Add(self.search_btn, flag=wx.ALL, border=5)
        search_and_sort_box.Add(self.sort_btn, flag=wx.ALL, border=5)
        vbox_files.Add(search_and_sort_box, flag=wx.EXPAND | wx.ALL, border=10)

        # 文件列表
        self.filePanel = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        self.filePanel.SetScrollRate(20, 20)
        self.fileList = wx.BoxSizer(wx.VERTICAL)
        self.filePanel.SetSizer(self.fileList)
        vbox_files.Add(self.filePanel, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        hbox.Add(vbox_files, proportion=2, flag=wx.EXPAND | wx.ALL, border=10)

        vbox.Add(hbox, proportion=1, flag=wx.EXPAND)

        panel.SetSizer(vbox)

        self.SetTitle('电池数据记录器')
        self.SetSize((800, 600))
        self.Centre()

        # 设置应用程序图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
        self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICO))

    def OnCreateDirectory(self, event):
        dlg = wx.TextEntryDialog(self, '请输入目录名称', '创建目录')
        if dlg.ShowModal() == wx.ID_OK:
            dir_name = dlg.GetValue()
            if dir_name and dir_name not in self.directories:
                self.directories[dir_name] = []
                self.dirList.InsertItem(self.dirList.GetItemCount(), dir_name)
                self.SaveDirectoryData()
        dlg.Destroy()

    def OnUploadFile(self, event):
        if not self.current_directory:
            wx.MessageBox('请先选择一个目录', '提示', wx.OK | wx.ICON_INFORMATION)
            return

        file_path = self.filePicker.GetPath()
        if file_path:
            file_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 显示上传进度条
            with wx.ProgressDialog("文件上传中", "请等待...", maximum=100, parent=self) as dlg:
                dlg.Pulse()

                # 复制文件到指定目录
                save_dir = os.path.join('uploaded_files', self.current_directory)
                os.makedirs(save_dir, exist_ok=True)
                new_file_path = os.path.join(save_dir, file_name)
                shutil.copyfile(file_path, new_file_path)

                dlg.Update(100)

            # 更新目录信息
            self.directories[self.current_directory].append(
                {'name': file_name, 'timestamp': timestamp, 'path': new_file_path})
            self.SaveDirectoryData()

            # 更新文件列表
            self.LoadFiles(self.current_directory)

            wx.MessageBox('文件上传成功！', '提示', wx.OK | wx.ICON_INFORMATION)

    def OnDirSelected(self, event):
        self.current_directory = self.dirList.GetItemText(event.GetIndex())
        self.LoadFiles(self.current_directory)
        self.HighlightSelectedDirectory(event.GetIndex())

    def HighlightSelectedDirectory(self, index):
        # 重置所有目录项的背景颜色为白色
        for i in range(self.dirList.GetItemCount()):
            self.dirList.SetItemBackgroundColour(i, wx.Colour(255, 255, 255))
        # 为选中的目录项设置背景颜色
        self.dirList.SetItemBackgroundColour(index, wx.Colour(173, 216, 230))
        self.dirList.Refresh()

    def OnRightClick(self, event):
        item, flags = self.dirList.HitTest(event.GetPosition())
        if item != wx.NOT_FOUND and flags & wx.LIST_HITTEST_ONITEM:
            self.dirList.Select(item)
            menu = wx.Menu()
            rename_item = menu.Append(wx.ID_ANY, '重命名')
            delete_item = menu.Append(wx.ID_ANY, '删除')
            self.Bind(wx.EVT_MENU, partial(self.OnRenameDirectory, item=item), rename_item)
            self.Bind(wx.EVT_MENU, partial(self.OnDeleteDirectory, item=item), delete_item)
            self.PopupMenu(menu)
            menu.Destroy()

    def OnRenameDirectory(self, event, item):
        old_name = self.dirList.GetItemText(item)
        dlg = wx.TextEntryDialog(self, '请输入新目录名称', '重命名目录', value=old_name)
        if dlg.ShowModal() == wx.ID_OK:
            new_name = dlg.GetValue()
            if new_name and new_name not in self.directories:
                self.directories[new_name] = self.directories.pop(old_name)
                self.dirList.SetItemText(item, new_name)
                self.SaveDirectoryData()
        dlg.Destroy()

    def OnDeleteDirectory(self, event, item):
        dir_name = self.dirList.GetItemText(item)
        if wx.MessageBox(f'确认删除目录 {dir_name} 吗？', '确认', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            del self.directories[dir_name]
            self.dirList.DeleteItem(item)
            self.SaveDirectoryData()
            if self.current_directory == dir_name:
                self.current_directory = None
                self.LoadFiles(None)

    def OnSortFiles(self, event):
        if self.current_directory and self.current_directory in self.directories:
            self.directories[self.current_directory].sort(key=lambda x: x['timestamp'])
            self.LoadFiles(self.current_directory)

    def OnSearchFiles(self, event):
        search_text = self.search_text.GetValue().lower()
        if self.current_directory and self.current_directory in self.directories:
            filtered_files = [file for file in self.directories[self.current_directory]
                              if search_text in file['name'].lower() or search_text in file['timestamp']]
            self.LoadFiles(self.current_directory, filtered_files)

    def OnDeleteFile(self, file_info):
        try:
            os.remove(file_info['path'])
            self.directories[self.current_directory] = [f for f in self.directories[self.current_directory] if
                                                        f['name'] != file_info['name']]
            self.SaveDirectoryData()
            self.LoadFiles(self.current_directory)
            wx.MessageBox('文件删除成功！', '提示', wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f'删除文件时发生错误: {e}', '错误', wx.OK | wx.ICON_ERROR)

    def OnDownloadFile(self, file_info):
        save_dialog = wx.FileDialog(self, "保存文件", wildcard="*.*", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        save_dialog.SetFilename(file_info['name'])

        if save_dialog.ShowModal() == wx.ID_OK:
            download_path = save_dialog.GetPath()

            # 显示下载进度条
            with wx.ProgressDialog("文件下载中", "请等待...", maximum=100, parent=self) as dlg:
                dlg.Pulse()
                shutil.copyfile(file_info['path'], download_path)
                dlg.Update(100)

            wx.MessageBox('文件下载成功！', '提示', wx.OK | wx.ICON_INFORMATION)

        save_dialog.Destroy()

    def OnOpenFile(self, file_info):
        try:
            os.startfile(file_info['path'])
        except Exception as e:
            wx.MessageBox(f'打开文件时发生错误: {e}', '错误', wx.OK | wx.ICON_ERROR)

    def OnOpenFolder(self, file_info):
        try:
            folder_path = os.path.dirname(file_info['path'])
            os.startfile(folder_path)
        except Exception as e:
            wx.MessageBox(f'打开文件夹时发生错误: {e}', '错误', wx.OK | wx.ICON_ERROR)

    def LoadDirectoryData(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as file:
                self.directories = json.load(file)
                for dir_name in self.directories:
                    self.dirList.InsertItem(self.dirList.GetItemCount(), dir_name)

    def SaveDirectoryData(self):
        with open(self.data_file, 'w', encoding='utf-8') as file:
            json.dump(self.directories, file, ensure_ascii=False, indent=4)

    def LoadFiles(self, directory, files=None):
        # 清空当前文件列表
        for child in self.filePanel.GetChildren():
            child.Destroy()

        self.fileList.Clear(delete_windows=True)  # 清空文件列表

        # 重新加载文件列表
        if directory is not None:
            if files is None:
                files = self.directories[directory]
            for file_info in files:
                item = FileListItem(self.filePanel, file_info, self.OnDeleteFile, self.OnDownloadFile, self.OnOpenFile, self.OnOpenFolder)
                self.fileList.Add(item, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.filePanel.SetScrollbars(1, 1, 1, 1)
        self.filePanel.Layout()
        self.filePanel.Refresh()  # 刷新文件面板


if __name__ == '__main__':
    app = wx.App()
    frame = BatteryDataApp(None)
    frame.Show()
    app.MainLoop()
