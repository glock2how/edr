import os
import ConfigParser

class EDRConfig(object):
    def __init__(self, config_file='config/config.ini'):
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.join(
            os.path.abspath(os.path.dirname(__file__)), config_file))

    def edr_version(self):
        return self.config.get('general', 'version')

    def edr_api_key(self):
        return self.config.get('edr', 'edr_api_key')

    def edr_server(self):
        return self.config.get('edr', 'edr_server')

    def edr_needs_u_novelty_threshold(self):
        return int(self.config.get('edr', 'edr_needs_u_novelty_threshold'))

    def inara_api_key(self):
        return self.config.get('inara', 'inara_api_key')

    def inara_endpoint(self):
        return self.config.get('inara', 'inara_endpoint')

    def intel_even_if_clean(self):
        return self.config.getboolean('scans', 'intel_even_if_clean')

    def intel_bounty_threshold(self):
        return self.config.getint('scans', 'intel_bounty_threshold')

    def legal_records_recent_threshold(self):
        return int(self.config.get('scans', 'legal_records_recent_threshold'))
    
    def legal_records_check_interval(self):
        return int(self.config.get('scans', 'legal_records_check_interval'))

    def legal_records_max_age(self):
        return int(self.config.get('scans', 'legal_records_max_age'))

    def system_novelty_threshold(self):
        return int(self.config.get('novelty', 'system_novelty_threshold'))

    def place_novelty_threshold(self):
        return int(self.config.get('novelty', 'place_novelty_threshold'))

    def ship_novelty_threshold(self):
        return int(self.config.get('novelty', 'ship_novelty_threshold'))

    def cognitive_novelty_threshold(self):
        return int(self.config.get('novelty', 'cognitive_novelty_threshold'))

    def systems_max_age(self):
        return int(self.config.get('lrucaches', 'systems_max_age'))

    def cmdrs_max_age(self):
        return int(self.config.get('lrucaches', 'cmdrs_max_age'))

    def cmdrsdex_max_age(self):
        return int(self.config.get('lrucaches', 'cmdrsdex_max_age'))

    def inara_max_age(self):
        return int(self.config.get('lrucaches', 'inara_max_age'))

    def blips_max_age(self):
        return int(self.config.get('lrucaches', 'blips_max_age'))

    def scans_max_age(self):
        return int(self.config.get('lrucaches', 'scans_max_age'))

    def traffic_max_age(self):
        return int(self.config.get('lrucaches', 'traffic_max_age'))

    def crimes_max_age(self):
        return int(self.config.get('lrucaches', 'crimes_max_age'))

    def lru_max_size(self):
        return int(self.config.get('lrucaches', 'lru_max_size'))

    def outlaws_max_age(self):
        return int(self.config.get('outlaws', 'outlaws_max_age'))

    def outlaws_max_recents(self):
        return int(self.config.get('outlaws', 'outlaws_max_recents'))

    def logging_level(self):
        return self.config.get('general', 'logging_level')

    def sitreps_timespan(self):
        return int(self.config.get('sitreps', 'sitreps_timespan'))

    def sitreps_max_age(self):
        return int(self.config.get('sitreps', 'sitreps_max_age'))

    def reports_check_interval(self):
        return int(self.config.get('sitreps', 'reports_check_interval'))

    def notams_check_interval(self):
        return int(self.config.get('sitreps', 'notams_check_interval'))

    def notams_max_age(self):
        return int(self.config.get('sitreps', 'notams_max_age'))

    def recon_recent_threshold(self):
        return int(self.config.get('sitreps', 'recon_recent_threshold'))

    def outlaws_recent_threshold(self):
        return int(self.config.get('sitreps', 'outlaws_recent_threshold'))

    def crimes_recent_threshold(self):
        return int(self.config.get('sitreps', 'crimes_recent_threshold'))

    def traffic_recent_threshold(self):
        return int(self.config.get('sitreps', 'traffic_recent_threshold'))