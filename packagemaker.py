import commands
import itertools
import os

import configuration


def read_history():
    os.chdir(configuration.BASE_PATH)
    os.system('git merge spinach/master')
    status, history = commands.getstatusoutput(
        'git log --pretty=format:"%H\t%an\t%ae\t%ad\t%s\t%P" --since ' + configuration.BASE_DATE)
    lines = history.split("\n")
    lines.reverse()
    base_hash = lines[0].split('\t')[5]
    array_fields = map(lambda l: l.split('\t'), lines)
    body_output = commands.getoutput(
        'git log --pretty=format:"|%b|" --since ' + configuration.BASE_DATE)
    array_body = body_output.split('|\n|')
    array_body[0] = array_body[0][1:]
    array_body.reverse()
    array_body[0] = array_body[0][:-1]
    (array_cur_hash, array_name, array_email, array_date, array_msg, array_par) = zip(
        *array_fields)

    def get_files(hash_code):
        cur_hash = str(hash_code)
        _, diffs = commands.getstatusoutput(
            'git diff ' + base_hash + ' ' + cur_hash + ' --name-status')
        file_diffs = diffs.split('\n')
        status_file = map(lambda fd: (str(fd[0]), str(fd[1:]).strip()), file_diffs)
        status_file.sort()
        it = itertools.groupby(status_file, lambda x: x[0])
        return dict([(k, [vv[1] for vv in v]) for k, v in it])

    array_files = map(lambda x: get_files(x), array_cur_hash)
    return array_cur_hash, array_name, array_email, array_date, array_msg, array_par,\
        array_files, array_body, base_hash


def copy_file(src, dst):
    # Please use abs path when setting ' + src
    assert os.path.isabs(src)
    # src + ' does not exist!'
    assert os.path.exists(src)
    # dst + ' is not a existed directory or non-exist file!'
    assert not os.path.exists(dst) ^ os.path.isdir(dst)
    return os.system('cp ' + src + ' ' + dst)


def create_package():
    base = configuration.OUTPUT_PATH
    if not os.path.exists(base):
        os.mkdir(base, 0775)
    os.chdir(base)
    os.system('rm -rf *')
    os.system('git init')
    map(lambda p: copy_file(p, base), configuration.OTHER_PATHS.split(','))
    os.system('git add -A .')
    os.system('git commit -m "initial commit"')
    return commands.getoutput('git rev-parse HEAD')


def create_path_and_copy_from_spark(
        handle,
        spark_base=configuration.BASE_PATH,
        package_base=configuration.OUTPUT_PATH):
    def create_directory(dir):
        parent_dir = os.path.dirname(dir)
        if not os.path.exists(parent_dir):
            create_directory(parent_dir)
        os.mkdir(dir, 0775)
    assert not os.path.isabs(handle)
    if handle.startswith('dev') or handle in configuration.BLACKLIST:
        # skip
        return
    file_dir = os.path.dirname(handle)
    position = file_dir.find('src')
    dst_dir = file_dir if position < 0 else file_dir[position:]
    abs_dst_dir = os.path.join(package_base, dst_dir)
    if not os.path.exists(abs_dst_dir):
        create_directory(abs_dst_dir)
    return copy_file(os.path.join(spark_base, handle), abs_dst_dir)


def rebuild_one_commit(cur_hash, name, email, date, msg, parent, file_dict, body, commit_map):
    os.chdir(configuration.BASE_PATH)
    commands.getoutput('git reset --hard ' + cur_hash)
    os.chdir(configuration.OUTPUT_PATH)
    if parent.find(' ') > 0:
        parent = parent[:parent.find(' ')]
    commands.getoutput('git reset --hard ' + commit_map[parent])
    os.system('rm -rf src/')
    files = [single_file for file_list in file_dict.values() for single_file in file_list]
    map(lambda h: create_path_and_copy_from_spark(h), files)
    commands.getoutput('git add -A .')
    date_option = ' --date="' + date + '"'
    escaped_msg = msg.replace('"', '\\"').replace('`', '\\`')
    escaped_body = body.replace('"', '\\"').replace('`', '\\`')
    msg_option = ' -m "' + escaped_msg + '\n\n' + escaped_body + '"'
    author_option = ' --author="' + name + ' <' + email + '>"'
    all_options = author_option + date_option + msg_option
    print all_options
    os.system('git commit' + all_options)
    commit_map[cur_hash] = commands.getoutput('git rev-parse HEAD')
    return


def rebuild_history(
        package_base,
        cur_hashes,
        names, emails, dates, msgs, parents, files, bodies, base_hash):
    cnt = len(cur_hashes)
    commit_map = dict()
    commit_map[base_hash] = package_base
    for i in range(cnt):
        cur_hash = cur_hashes[i]
        name = names[i]
        email = emails[i]
        date = dates[i]
        msg = msgs[i]
        parent = parents[i]
        file_dict = files[i]
        body = bodies[i]
        rebuild_one_commit(cur_hash, name, email, date, msg, parent, file_dict, body, commit_map)
    return


def __main__():
    history = read_history()
    package_base = create_package()
    rebuild_history(package_base, *history)


__main__()
