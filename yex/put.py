import io
import yex.document
import yex.parse
import yex.exception
import argparse
import logging

yex_logger = logging.getLogger('yex')
macros_logger = logging.getLogger('yex.macros')
commands_logger = logging.getLogger('yex.commands')

class PutError(Exception):
    def __init__(self,
            message,
            context):
        self.message = message
        self.context = context

    def __repr__(self):
        return self.context

    def __str__(self):
        return self.context

def put(source,
        doc = None,
        catch = True,
        target = None,
        ):

    if doc is None:
        doc = yex.document.Document()

    t = yex.parse.Tokeniser(
            doc = doc,
            source = source,
            )
    e = yex.parse.Expander(
            t,
            on_eof='exhaust',
            )

    try:
        for item in e:
            commands_logger.debug("  -- resulting in: %s", item)

            doc['_mode'].handle(
                    item=item,
                    tokens=e,
                    )

        if target:
            doc.save(target)
        else:
            commands_logger.warning("not saving because no filename given")

    except Exception as exception:
        if not catch:
            raise

        message = f'{exception.__class__.__name__} {exception}'
        context = t.error_position(message)

        raise PutError(
                message = message,
                context = context,
                )
