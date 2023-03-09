from aiohttp import web
import aiofiles
import asyncio
import os
from textwrap import dedent
from asyncio.subprocess import create_subprocess_shell
import logging


logging.basicConfig(
    format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-5s [%(asctime)s]  %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger('downloader')


SIZE_KB = 100
BYTES_IN_KB = 1024


async def archive(request):
    response = web.StreamResponse()
    original_folder = request.match_info.get('archive_hash')
    archive_path = os.path.join(os.getcwd(), 'test_photos', original_folder)
    if os.path.isdir(archive_path) and os.listdir(archive_path):
        response.headers['Content-Disposition'] = f'attachment; filename="archive_{original_folder}.zip"'
        response.headers['Content-Type'] = 'multipart/form-data'
        await response.prepare(request)
        cmd = f'zip -r - {" ".join(os.listdir(archive_path))}'
        process = await create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=archive_path
        )
        byte = SIZE_KB * BYTES_IN_KB
        try:
            while True:
                logger.info('Sending archive chunk ...')
                await asyncio.sleep(1)
                stdout = await process.stdout.read(byte)
                await response.write(stdout)
                if process.stdout.at_eof():
                    await response.write_eof(stdout)
                    break
        except asyncio.CancelledError:
            logger.warning('Download was interrupted')
            raise
    else:
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

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),

    ])
    web.run_app(app)
