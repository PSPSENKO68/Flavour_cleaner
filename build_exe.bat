@echo off
echo Đang cài đặt thư viện cần thiết...
pip install pyinstaller openpyxl

echo.
echo Bắt đầu đóng gói ứng dụng thành file .exe...
echo Quá trình này có thể mất vài phút...
pyinstaller --noconfirm --onedir --windowed --add-data "patterns.txt;." gui.py

echo.
echo Hoàn thành!
echo Ứng dụng của bạn (flavour-cleaner) đã được tạo tại thư mục "dist\gui\".
echo Bạn có thể đổi tên thư mục "gui" thành "flavour-cleaner-app" và chia sẻ cho người khác.
echo Bên trong thư mục đó có file "gui.exe", bạn chạy file này để mở ứng dụng.
pause
