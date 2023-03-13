import logging
import aiofiles
import asyncio
import os
import argparse

from textwrap import dedent
from asyncio.subprocess import create_subprocess_exec
from aiohttp import web


async def archive(request):
    response = web.StreamResponse()
    parser_args = request.app.parser_args
    if parser_args.path:
        original_folder = os.path.split(parser_args.path)[1]
        archive_path = parser_args.path
    else:
        original_folder = request.match_info.get('archive_hash')
        archive_path = os.path.join(os.getcwd(), 'test_photos', original_folder)
    if os.path.isdir(archive_path) and os.listdir(archive_path):
        response.headers['Content-Disposition'] = f'attachment; filename="archive_{original_folder}.zip"'
        response.headers['Content-Type'] = 'multipart/form-data'
        await response.prepare(request)
        cmd = ['zip', '-r', '-', *os.listdir(archive_path)]
        process = await create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=archive_path
        )
        byte = request.app.size_kb * request.app.bytes_in_kb
        try:
            while True:
                if parser_args.logging:
                    logger.info('Sending archive chunk ...')
                if parser_args.delay:
                    await asyncio.sleep(parser_args.delay)
                stdout = await process.stdout.read(byte)
                await response.write(stdout)
                if process.stdout.at_eof():
                    await response.write_eof(stdout)
                    break
        except KeyboardInterrupt:
            process.terminate()
            await process.communicate()
        except asyncio.CancelledError:
            if parser_args.logging:
                logger.warning('Download was interrupted')
            process.terminate()
            await process.communicate()
            raise
        return

    raise web.HTTPNotFound(
        text=dedent(
            '''
            404 - страница не найдена.
            Архив не существует или был удален
            '''
            )
        )


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    SIZE_KB = 100
    BYTES_IN_KB = 1024

    parser = argparse.ArgumentParser(prog='DownloadService', description='Сервис для скачивания файлов')
    parser.add_argument('-l', '--logging', required=False, action='store_true', help='Включение логирования')
    parser.add_argument('-dl', '--delay', required=False, default=0, type=int,
                        help='Задержка ответа при скачивании, сек')
    parser.add_argument('-p', '--path', required=False, help='Полный путь к каталогу с файлами')
    args = parser.parse_args()

    if args.logging:
        logging.basicConfig(
            format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-5s [%(asctime)s]  %(message)s',
            level=logging.DEBUG
        )
        logger = logging.getLogger('downloader')

    app = web.Application()
    app.parser_args = args
    app.size_kb = SIZE_KB
    app.bytes_in_kb = BYTES_IN_KB
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),

    ])
    web.run_app(app)
