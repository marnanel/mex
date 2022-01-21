import io
import mex.state
import mex.token

def put(text):

    state = mex.state.State()
    result = ''

    with io.StringIO(text) as f:

        tokens = mex.token.Tokeniser(
                state = state,
                source = f,
                )

        for item in tokens:

            if item.category in (item.LETTER, item.SPACE, item.OTHER):
                result += item.ch
            else:
                raise ValueError(f"Don't know category for {item}")

    return result

if __name__=='__main__':
    print(put("If you see this, it works."))
