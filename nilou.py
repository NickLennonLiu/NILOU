from time import sleep
import os
from secret_true import api, proxies, username
from config import META, PREVIEW, IMAGE, CAPTION
import requests
import json
import heapq

uri = "https://danbooru.donmai.us"

auth = {
	"api_key": api,
	"login": username
}

use_fields = {"source", "tag_string", "fav_count", "tag_count_general", "tag_count_artist", "tag_count_character",
			  "file_url", "preview_file_url", "parent_id"}

def process_tags(tag_list):
	tag_string = [tag.replace('_', ' ') for tag in tag_list]
	tag_string = [tag.replace('(', '\\(') for tag in tag_string]
	tag_string = [tag.replace(')', '\\)') for tag in tag_string]
	return ', '.join(tag_string)

def resize_image(image):
	raise NotImplementedError

def get_suggested_tags(keyword):
	payload = {
		**auth,
		"search[name_matches]": f"*{keyword}*",
		"search[hide_empty]": 1,
		"limit": 10,
		"type": "json",
		"search[order]": "count"
	}
	res = requests.get(uri + "/tags.json", proxies=proxies, params=payload)
	if res.status_code != 200:
		print(f"Failed to get related tags!")
		return None
	ls = json.loads(res.content)
	return ls

def get_pages(tags, page=1, limit=20):
	payload = {
		**auth,
		"tags": tags,
		"format": "json",
		"page": page,
		"limit": limit
	}
	res = requests.get(uri + "/posts.json", proxies=proxies, params=payload)
	if res.status_code != 200:
		print(f"Failed to get {tags} on page {page}")
		return
	ls = json.loads(res.content)
	return ls

def get_search_result(tags, num, limit=20):
	pages = []
	for i in range(int(num/limit)):
		sleep(1)
		page_result = []
		page = get_pages(tags, i+1)
		for image in page:
			try:
				page_result.append({
					key:image[key] for key in use_fields
				})
			except KeyError as e:
				continue
		print(f"Fetched page {i+1}")
		pages.append(page_result)
	return pages

def get_preview(search_result, interval=1):
	print(f"Downloading {len(search_result)} images")
	for image in search_result:
		if image['parent_id'] == "null":
			continue
		sleep(interval)
		filename = image["preview_file_url"].split('/')[-1].split('.')[0]
		r = requests.get(image["preview_file_url"], proxies=proxies)
		with open(os.path.join(PREVIEW, filename+".jpg"), 'wb') as f:
			f.write(r.content)
		with open(os.path.join(META, filename+".json"), 'w') as f:
			json.dump(image, f)
		with open(os.path.join(CAPTION, filename + ".txt"), 'w') as f:
			f.write(process_tags(image["tag_string"].split(' ')))

def get_topk_tags(topk, output_file=None):
	all_tags = {}
	for filename in os.listdir(META):
		with open(os.path.join(META, filename), 'r') as f:
			tags = json.load(f)["tag_string"].split(' ')
			for tag in tags:
				if tag in all_tags:
					all_tags[tag] += 1
				else:
					all_tags[tag] = 1
	k_tags = heapq.nlargest(topk, all_tags, key=all_tags.__getitem__)
	print(f"Top {topk} tags are: {k_tags}")
	if output_file:
		print(f"Saving to {output_file}")
		with open(output_file, "w") as f:
			f.write(', '.join(k_tags))

def remove_undesired_pics():
	hash_list = []
	for filename in os.listdir(PREVIEW):
		image_hash = os.path.splitext(filename)[0]
		hash_list.append(image_hash)
	for filename in os.listdir(META):
		image_hash = os.path.splitext(filename)[0]
		if image_hash not in hash_list:
			os.remove(os.path.join(META, image_hash+".json"))
	for filename in os.listdir(CAPTION):
		image_hash = os.path.splitext(filename)[0]
		if image_hash not in hash_list:
			os.remove(os.path.join(CAPTION, image_hash+".txt"))

def get_original_images():
	for filename in os.listdir(META):
		image_hash = os.path.splitext(filename)[0]
		with open(os.path.join(META, filename), 'r') as f:
			meta = json.load(f)
		r = requests.get(meta["file_url"], proxies=proxies)
		with open(os.path.join(IMAGE, image_hash + ".jpg"), 'wb') as f:
			f.write(r.content)
		

def make_dirs():
	if not os.path.exists(PREVIEW):
		os.makedirs(PREVIEW)
	if not os.path.exists(IMAGE):
		os.makedirs(IMAGE)
	if not os.path.exists(CAPTION):
		os.makedirs(CAPTION)
	if not os.path.exists(META):
		os.makedirs(META)

def search_tag():
	keyword = input("input your keyword: ")
	tag_list = get_suggested_tags(keyword)
	
	if len(tag_list):
		print("Are you searching for: \nidx\t\tname\t\t\tpost_count\t\tcategory")
		for idx, tag in enumerate(tag_list):
			print(f"{idx}\t\t{tag['name']}\t\t\t{tag['post_count']}\t\t{tag['category']}")
	
		index = int(input("Choose your tag: "))
		tags = tag_list[index]['name']
	else:
		print("No tag found! try again?")
		exit(0)
	return tags

def set_number():
	num = input("number of pictures you want(100 by default): ")
	if num == "":
		num = 100
	else:
		num = int(num)
	return num

def clear_remains():
	for filename in os.listdir(PREVIEW):
		os.remove(os.path.join(PREVIEW, filename))
	for filename in os.listdir(CAPTION):
		os.remove(os.path.join(CAPTION, filename))
	for filename in os.listdir(IMAGE):
		os.remove(os.path.join(IMAGE, filename))
	for filename in os.listdir(META):
		os.remove(os.path.join(META, filename))

def check_remains():
	if len(os.listdir(PREVIEW)):
		remove = input("Do you wish to remove previous results? : [y]/n")
		if not len(remove):
			remove = "y"
		if remove == "y":
			clear_remains()
		else:
			print("I will leave you to deal with them.")
			exit(0)

if __name__ == "__main__":
	make_dirs()
	check_remains()

	tags = search_tag()
	num = set_number()
	
	
	#get_search_result(PREVIEW, "./meta", "nilou_(genshin_impact)", 100)
	pages = get_search_result(tags, num)
	for page in pages:
		get_preview(page)

	input("now delete the pictures you don't want, after that, press any key to continue: ")
	remove_undesired_pics()
	get_topk_tags(20, "./top20_tags.txt")
	get_original_images()

