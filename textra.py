from subprocess import run
from os import chmod, makedirs, path
from collections import deque
from sys import argv
from json import load

'''
TODO
Get target_dir argument working for all directory possibilities
'''

example_config = {
    "frontend": {
        "react": {
            "packages": [
                "nodemon",
            ]
        }
    },
    "backend": {
        "flask": {
            "packages": [
                "flask-cors",
            ]
        }
    },
#     "database": {
#         "sqlite": {
#             "db_name": "test",
#             "host": "localhost",
#             "user": "test_user",
#             "password": "password123",
#             "port": "5432"
#         }
#     },
#     "web_server": {
#         "nginx": {
#             "server_name": "127.0.0.1",
#             "proxy_pass": "http://127.0.0.1:8000"
#         }
#     },
}

lexicon = {
    "frontend": {
        "react": {
            "packages",
        }
    },
    "backend": {
        "flask": {
            "packages"
        }
    },
    "database": {
        "sqlite": {
            "db_name",
            "host",
            "user",
            "password",
            "port"
        }
    },
    "web_server": {
        "nginx": {
            "server_name",
            "proxy_pass",
        }
    }
}

commands = {
    "react": {
        "init": "yarn create react-app frontend && cd frontend",
        "packages": "yarn add ",
    },
    "flask": {
        "init": "python3 -m venv ./backend/.venv && ./backend .venv/bin/activate && pip3 install flask && pip3 freeze > requirements.txt",
        "packages": "pip3 install ",
    }
}

files = {
    "flask": {
        "init": { # add name
            "import": ["from flask import Flask\n"],
            "core": [
                "\napp = Flask(__name__)\n",
                "\n",
                "@app.route('/')\n",
                "def hello_world():\n",
                "\treturn 'Hello, World!'\n",
            ]
        },
        "packages": {
            "flask-cors": {
                "import": [
                    {
                        "line": "from flask_cors import CORS\n",
                        "min_index": 1
                    }
                ],
                "core": [
                    {
                        "line": "CORS(app)\n",
                        "min_index": 1
                    }
                ],
            }
        }
    }
}

# somehow incorporate core files for each tool
tool_dir = {
    "react": "frontend",
    "flask": "backend/app.py",
}

def parse(config):
    scripts = {}
    packages = {}

    try:
        for portion in config:
            if portion in lexicon.keys():
                tools = config[portion]
                for tool in tools.keys():
                    if tool in lexicon[portion]:
                        scripts[tool] = []
                        scripts[tool] += [commands[tool]["init"]]
                        
                        for keyword in lexicon[portion][tool]:
                            if keyword in tools[tool]:
                                cmd = commands[tool][keyword]
                                if keyword == "packages":
                                    packages[tool] = tools[tool][keyword]
                                    for pkg in tools[tool][keyword]:
                                        scripts[tool] += [cmd + str(pkg)]
                            else:
                                raise Exception(f'ERROR: \'{keyword}\' not recognized for \'{tool}\'')

                    else:
                        raise Exception(f'ERROR: \'{tool}\' not supported')
            else:
                raise Exception(f'ERROR: \'{portion}\' not recognized')

    except Exception as e:
        print(e)
        return []

    return (scripts, packages)

def make_sh(scripts, target_dir):
    paths = []

    try:
        makedirs(f"{target_dir}/shell_scripts")
    except Exception as e:
        print(e)

    for tool in scripts.keys():
        fname = f'{tool}.sh'
        paths += [f'{target_dir}/shell_scripts/{fname}']
        f = open(f'{target_dir}/shell_scripts/{fname}', "w")
        f.write("#!/bin/sh\n")
        for script in scripts[tool]:
            f.write(script)
            f.write("\n")
        f.close()
        chmod(f'{target_dir}/shell_scripts/{fname}', 0o777)

    return paths

def exe_sh(paths):
    for path in paths:
        run(path)

# error check target directory
def make_files(tool, target_packages, target_dir):
    if tool not in files:
        # raise Exception(f'ERROR: \'{tool}\' not recognized for file creation)')
        return
    
    source = files[tool]
    line_map = {}

    # this is where applicable package lines are selected
    for source_section,v in source.items():
        if source_section == "init":
            for item in v:
                if item not in line_map:
                    line_map[item] = []
                for it in source[source_section][item]:
                    line_map[item] += [it]
        elif source_section == "packages":
            all_packages = source[source_section]

            for pkg in all_packages:
                if pkg in target_packages:
                    for portion in all_packages[pkg]:
                        for item in all_packages[pkg][portion]:
                            if portion not in line_map:
                                line_map[portion] = []
                            line_map[portion] += [item]

    lines = []
    boiler_q = deque()
    pkg_q = deque()

    for _, code_line in line_map.items():
        current_code = []
        for line in code_line:
            if type(line) is str:
                boiler_q += [line]
            else:
                pkg_q += [line]

        while boiler_q or pkg_q:
            b_line = boiler_q.popleft() if boiler_q else None
            pkg_line = pkg_q.popleft() if pkg_q else None
            if b_line is None:
                current_code += [pkg_line["line"]]
            elif pkg_line is None:
                current_code += [b_line]
            elif pkg_line and pkg_line["min_index"] > len(current_code):
                current_code += [b_line]
                pkg_q.appendleft(pkg_line)
            elif pkg_line and pkg_line["min_index"] <= len(current_code):
                current_code += [pkg_line["line"]]
                boiler_q.appendleft(b_line)
            elif b_line is not None:
                current_code += [b_line]

        for line in current_code:
            lines.append(line)

    # add core files for each tool
    fpath = f'{tool_dir[tool]}'

    f = open(f'{target_dir}/{fpath}', "w")
    for line in lines:
        f.write(line)
    f.close()

def main():
    if len(argv) != 5:
        print("Usage")
        return
    
    f = argv[1]
    d = argv[3]

    if f != "-f" or d != "-d":
        print("Usage 2")
        return
    
    config_file_path = argv[2]
    target_dir = argv[4]

    with open(config_file_path) as config_file:
        cfg = load(config_file)
    
    scripts, packages = parse(cfg)
    paths = make_sh(scripts, target_dir)
    exe_sh(paths)
    for tool, target_packages in packages.items():
        make_files(tool, target_packages, target_dir)
    
if __name__ == '__main__':
    main()