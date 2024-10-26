import os
import shutil
import argparse
import anitopy
import pathlib
import re

def get_season_number_from_dir(directory_name):
    match = re.search(r'Season (\d+)', directory_name)
    if match:
        return int(match.group(1))
    return None

def get_season_number(anime_path, anime_info, default_season=1):
    # Check for existing season directories and use their numbers
    season_number = get_season_number_from_dir(anime_path)
    if season_number is not None:
        return season_number
    
    # Fall back to using anime_info's season number or default
    return int(anime_info.get('anime_season', default_season))

def gather_episodes(anime_path, anime_title, default_season, has_season_subdirs):
    rename_episodes = {}
    for episode in os.listdir(anime_path):
        try:
            episode_info = anitopy.parse(episode)

            if 'episode_number' not in episode_info or 'episode_number_alt' in episode_info:
                print(f'Skip episode {episode} due to missing or alternative episode number')
                continue

            suffixes = pathlib.Path(episode).suffixes
            if not suffixes:
                print(f'Skip episode {episode} due to no suffix')
                continue

            if len(suffixes) > 2:
                suffixes = suffixes[-2:]

            ext = suffixes[-1]
            
            if has_season_subdirs:
                anime_season = default_season
            else:
                # Determine season number from episode_info or use default
                anime_season = int(episode_info.get('season_number', default_season))

            if ext in ['.mkv', '.mp4', '.mka']:
                anime_episode = int(episode_info['episode_number'])
                newEpName = '{} - S{:02}E{:02}{}'.format(anime_title, anime_season, anime_episode, ext)
            elif ext in ['.ass', '.srt']:
                anime_episode = int(episode_info['episode_number'])
                newEpName = '{} - S{:02}E{:02}{}'.format(anime_title, anime_season, anime_episode, ''.join(suffixes))
            else:
                print(f'Skip episode {episode} due to unsupported extension')
                continue

            # Determine target path
            if has_season_subdirs:
                target_dir = anime_path
            else:
                target_dir = os.path.join(anime_path, 'Season {:02}'.format(anime_season))
            
            rename_episodes[os.path.join(anime_path, episode)] = os.path.join(target_dir, newEpName)

        except Exception as e:
            print(f'Error processing episode {episode}: {e}')
            continue

    return rename_episodes

def create_and_move_files(rename_episodes, dry_run):
    # Move files to their new locations
    for oldPath, newPath in rename_episodes.items():
        target_dir = os.path.dirname(newPath)
        if not os.path.exists(target_dir):
            print(f'Creating directory {target_dir}')
            if not dry_run:
                os.makedirs(target_dir)
        print(f'Moving file from {oldPath} to {newPath}')
        if not dry_run:
            shutil.move(oldPath, newPath)
            
def check_arranged_marker(show_path):
    arranged_marker = os.path.join(show_path, '.bangumi_arranged')
    if os.path.exists(arranged_marker):
        return True
    return False

def create_arranged_marker(show_path, dry_run):
    if not dry_run:
        arranged_marker = os.path.join(show_path, '.bangumi_arranged')
        with open(arranged_marker, 'w') as f:
            f.write('This directory has been processed by the bangumi-arrange script.')

def process_show_directory(show_path, dry_run):
    print(f'Processing show directory: {show_path}')
    
    # Skip processing if the directory has already been arranged
    if check_arranged_marker(show_path):
        print(f'Skip directory {show_path} as it was already processed.')
        return

    if not os.path.isdir(show_path):
        print(f"The specified path is not a directory: {show_path}")
        return

    # Parse show directory to get anime info
    anime_info = anitopy.parse(os.path.basename(show_path))
    if 'anime_title' not in anime_info:
        print(f'Skip directory {show_path} due to missing title')
        return

    anime_title = anime_info['anime_title']

    files_in_show_path = [f for f in os.listdir(show_path) if os.path.isfile(os.path.join(show_path, f))]
    has_season_subdirs = any(os.path.isdir(os.path.join(show_path, d)) and re.match(r'Season \d+', d) for d in os.listdir(show_path))

    if files_in_show_path:
        default_season = get_season_number(show_path, anime_info)
        # Process files directly in show_path
        rename_episodes = gather_episodes(show_path, anime_title, default_season, has_season_subdirs)
        create_and_move_files(rename_episodes, dry_run)
    else:
        # Process each subdirectory if they exist
        for directory in os.listdir(show_path):
            anime_path = os.path.join(show_path, directory)
            if not os.path.isdir(anime_path):
                continue
            
            default_season = get_season_number(anime_path, anime_info)

            rename_episodes = gather_episodes(anime_path, anime_title, default_season, has_season_subdirs)
            create_and_move_files(rename_episodes, dry_run)
            
    create_arranged_marker(show_path, dry_run)

def main():
    parser = argparse.ArgumentParser(description="Organize and rename TV show files into a hierarchical directory structure.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--show-dir', type=str, help="Path to a single show directory.")
    group.add_argument('--shows', type=str, help="Path to a directory containing multiple show directories.")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without making any changes.")

    args = parser.parse_args()

    if args.show_dir:
        process_show_directory(args.show_dir, args.dry_run)
    elif args.shows:
        if not os.path.isdir(args.shows):
            sys.exit(f"The specified shows directory is not valid: {args.shows}")

        for dir_name in os.listdir(args.shows):
            show_path = os.path.join(args.shows, dir_name)
            if os.path.isdir(show_path):
                process_show_directory(show_path, args.dry_run)

if __name__ == '__main__':
    main()

