#!/usr/bin/env python3
import vim
import sys
import subprocess
import shlex


def _vimerr(errmsg):
    sys.stderr.write(errmsg)


def _fetchCodeBlock():
    buf = vim.current.buffer
    r, c = vim.current.window.cursor

    beginCapture = False
    finishCapture = False
    graphCodeBuf = ""

    start = -1
    end = -1

    # Find \graph upwards
    savebuf = buf[:r]
    for idx, line in enumerate(savebuf[::-1]):
        if line.rstrip() == "\endgraph":
            _vimerr("Please locate cursor INSIDE the graph block")
            return None
        if line.rstrip() == "\graph":
            start = r - idx - 1
            break

    if start == -1:
        _vimerr("Can't find graph")
        return None

    # print("Graph start at {}".format(start))

    for idx, line in enumerate(buf[start:]):
        # print("DBG:" + line)
        if line.rstrip() == "\graph" and not beginCapture:
            beginCapture = True
            continue
        if line.rstrip() == "\graph" and beginCapture:
            _vimerr("Nesting graph is not allowed")
            return
        if line.rstrip() == "\endgraph" and beginCapture:
            finishCapture = True
            end = start + idx
            break
        if beginCapture:
            graphCodeBuf = graphCodeBuf + "\n" + line

    if not finishCapture:
        _vimerr("Can't find End Of Graph {}".format("\\endgraph"))
        return

    return (start, end)


def DoGen():
    ret = _fetchCodeBlock()
    if ret is None:
        return
    s, e = ret
    codeb = "\n".join(vim.current.buffer[s + 1 : e])

    # print("S = {},E = {}".format(s, e))
    # print("Graph Code Block is\n{}\n".format(codeb))

    if codeb is None:
        _vimerr("Can't find graph")
        return
    graph = _callExternal(codeb)
    if graph is None:
        return

    # Clear the range and append the graph
    r = vim.current.buffer.range(s, e + 1)
    r.append("")
    for line in graph.split("\n"):
        r.append(line)


def _callExternal(buf):
    cmdarg = shlex.split("/usr/bin/graph-easy --as=ascii")
    proc = subprocess.Popen(
        cmdarg, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        out, err = proc.communicate(bytes(buf, "UTF-8"), timeout=2)
        if proc.returncode != 0:
            errmsg = "graph-easy call error, {}".format(err.decode("UTF-8"))
            _vimerr(errmsg)
            proc.stdin.close()
            proc.wait()
            return None
        proc.stdin.close()
    except subprocess.TimeoutExpired:
        proc.kill()
        _vimerr("graph-easy call time out")
        return None
    proc.wait()
    return str(out, "UTF-8")
