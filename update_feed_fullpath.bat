@echo off
REM update_feed_fullpath.bat — автогенерация feed.yml и пуш на GitHub
REM Положите этот файл в C:\feed и используйте в Планировщике задач

cd /d C:\feed

REM Запускаем python по полному пути
"C:\Users\ASUS Vivobook\AppData\Local\Python\bin\python.exe" make_feed.py

REM Добавляем только feed.yml и коммитим при изменениях
git add feed.yml
git commit -m "Автообновление feed.yml %DATE% %TIME%" 2>nul || echo no-changes

REM Пушим изменения в ветку main
git push origin main

REM Завершение (без pause — чтобы задача не висела)
exit /b 0
