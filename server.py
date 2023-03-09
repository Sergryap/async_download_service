from aiohttp import web
import aiofiles
import datetime
import asyncio
import hashlib
import os
from asyncio.subprocess import create_subprocess_shell

INTERVAL_SECS = 1


async def get_binary_zip_archive(original_folder, kb):
    hash_name = hashlib.md5(original_folder.encode('utf-8')).hexdigest()
    print(hash_name)
    byte = 1024 * kb
    all_stdout = bytes()
    cmd = f'zip -r - {" ".join(os.listdir(original_folder))}'
    process = await create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=original_folder
    )
    while True:
        stdout = await process.stdout.read(byte)
        all_stdout += stdout
        if process.stdout.at_eof():
            break

    return all_stdout


async def archive_old(request):
    response = web.StreamResponse()
    original_folder = request.match_info.get('archive_hash')
    archive_path = os.path.join(os.getcwd(), 'test_photos', original_folder)
    hash_name = hashlib.md5(original_folder.encode('utf-8')).hexdigest()
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    response.headers['Transfer-Encoding'] = r'chunked\r\n'
    # response.headers['Content-Type'] = 'multipart/form-data'
    cmd = f'zip -r - {" ".join(os.listdir(archive_path))}'
    process = await create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path
    )
    byte = 1024 * 300
    all_stdout = bytes()
    connection = r'keep-alive\r\n\r\n'
    while True:
        stdout = await process.stdout.read(byte)
        connection += rf'{stdout.hex()}\r\n{stdout}\r\n'
        all_stdout += stdout
        if process.stdout.at_eof():
            connection += rf'0\r\n\r\n'
            break
    response.headers['Connection'] = connection
    await response.prepare(request)
    await response.write(all_stdout)


async def archive(request):
    response = web.StreamResponse()
    original_folder = request.match_info.get('archive_hash')
    archive_path = os.path.join(os.getcwd(), 'test_photos', original_folder)
    hash_name = hashlib.md5(original_folder.encode('utf-8')).hexdigest()
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    response.headers['Transfer-Encoding'] = 'chunked'
    # response.headers['Content-Type'] = 'multipart/form-data'

    await response.prepare(request)
    cmd = f'zip -r - {" ".join(os.listdir(archive_path))}'
    process = await create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=archive_path
    )
    byte = 1024 * 300
    while True:
        stdout = await process.stdout.read(byte)
        await response.write(stdout)
        if process.stdout.at_eof():
            break




async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def uptime_handler(request):
    response = web.StreamResponse()

    # Большинство браузеров не отрисовывают частично загруженный контент, только если это не HTML.
    # Поэтому отправляем клиенту именно HTML, указываем это в Content-Type.
    response.headers['Content-Type'] = 'text/html'

    # Отправляет клиенту HTTP заголовки
    await response.prepare(request)

    while True:
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f'{formatted_date}<br>'  # <br> — HTML тег переноса строки

        # Отправляет клиенту очередную порцию ответа
        await response.write(message.encode('utf-8'))

        await asyncio.sleep(INTERVAL_SECS)


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        # web.get('/archive/7kna/', uptime_handler),
        web.get('/archive/{archive_hash}/', archive),

    ])
    web.run_app(app)
