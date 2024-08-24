import base64,datetime,json,logging,os,requests,secrets,zoneinfo
from icalendar import Calendar, Event, vCalAddress, vText
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

log_format = '%(asctime)s[%(filename)s:%(lineno)d][%(levelname)s] %(message)s'
logging.basicConfig(format=log_format, datefmt='%Y-%m-%d %H:%M:%S%z', level=logging.INFO)
ORIGIN_TZ=zoneinfo.ZoneInfo("Asia/Tokyo")

def get_schedule_data():
    try:
        response = requests.get(
            url="https://spla3.yuu26.com/api/coop-grouping/schedule",
            headers={
                "User-Agent": "SalmonrunCalendar/1.0(https://github.com/legnoh/salmonrun-calendar)",
            },
        )
        if response.status_code == 200:
            return response.json()['results']
        else:
            logging.error(f"get error response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.fatal(f"get exception: {e}")
        return None

def get_weapons_data():
    ua = UserAgent()
    try:
        response = requests.get(
            url = "https://wikiwiki.jp/splatoon3mix/サーモンラン/ブキ別立ち回り",
            headers = {'User-Agent': str(ua.chrome)}
        )
        if response.status_code == 200:
            weapons = {}
            html = response.content.decode(response.apparent_encoding)
            soup = BeautifulSoup(html, 'html.parser')
            weapons_html = soup.select("div#content div.h-scrollable:not(:first-child) > table > tbody > tr > td > a")
            for weapon_html in weapons_html:
                url = weapon_html.attrs["href"]
                if len(weapon_html.select("img")) != 0:
                    name = weapon_html.select_one("img").attrs["alt"]
                    weapons[name] = f"https://wikiwiki.jp{url}"
            return weapons
    except requests.exceptions.RequestException:
        logging.fatal("failed to get salmonrun weapon data")
        return None

def create_description(weapons:list, all_weapons:dict) -> str:
    description = ""
    for weapon in weapons:
        if weapon["name"] in all_weapons:
            description += f"# 編成評価:\nhttps://appmedia.jp/splatoon3/75973100#skd\n\n#ブキ\n\n## {weapon["name"]}\n{all_weapons[weapon["name"]]}\n\n"
    return description.strip()

if __name__ == '__main__':

    cal = Calendar()
    cal.add("X-WR-CALNAME", "サーモンラン")
    cal.add("X-APPLE-CALENDAR-COLOR", "#DE6233")

    all_weapons = get_weapons_data()
    schedule_data = get_schedule_data()

    for event_data in schedule_data:

        # uidを作る
        raw_uid = "{s}{t}".format(s=event_data['stage']['name'],t=event_data['start_time'])
        uid_enc = raw_uid.encode('utf-8')
        uid = base64.b64encode(uid_enc)

        event = Event()
        event.add('UID', uid)
        event.add('SUMMARY', "サーモンラン")
        event.add('DESCRIPTION', create_description(event_data["weapons"], all_weapons))
        event.add('DTSTART', datetime.datetime.fromisoformat(event_data['start_time']).astimezone(ORIGIN_TZ))
        event.add('DTEND', datetime.datetime.fromisoformat(event_data['end_time']).astimezone(ORIGIN_TZ))
        event.add('LOCATION', f"{event_data["boss"]["name"]}@{event_data['stage']['name']}")
        event.add('URL', f"https://wikiwiki.jp/splatoon3mix/サーモンラン/ステージ/{event_data['stage']['name']}", parameters={'VALUE': 'URI'})
        event.add('TRANSP', 'TRANSPARENT')

        for weapon in event_data["weapons"]:
            attendee = vCalAddress(f'MAILTO:{secrets.token_hex(16)}@example.com')
            attendee.params['cn'] = vText(weapon['name'])
            attendee.params['role'] = vText('REQ-PARTICIPANT')
            attendee.params['partstat'] = vText('ACCEPTED')
            event.add('ATTENDEE', attendee)

        cal.add_component(event)
    
    logging.info("# Output ics file")
    if not os.path.exists("./dist"):
        os.mkdir("./dist")
    with open("./dist/schedule.ics", mode='w') as f:
        f.write(cal.to_ical().decode("utf-8"))
    
    logging.info("All process was done successfully.")
