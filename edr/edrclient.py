# coding= utf-8
import datetime
import time

import Tkinter as tk
import ttk
import ttkHyperlinkLabel
import myNotebook as notebook
from config import config
import edrconfig

import lrucache
import edentities
import edrserver
import audiofeedback
import edrlog
import ingamemsg
import edrsystems
import edrcmdrs
import edroutlaws
import randomtips
import helpcontent
import edtime
import edrlegalrecords
from edri18n import _, _c, _edr, set_language

EDRLOG = edrlog.EDRLog()

class EDRClient(object):
    IN_GAME_MSG = ingamemsg.InGameMsg()
    AUDIO_FEEDBACK = audiofeedback.AudioFeedback()

    def __init__(self):
        edr_config = edrconfig.EDRConfig()
        set_language(config.get("language"))

        self.edr_version = edr_config.edr_version()
        EDRLOG.log(u"Version {}".format(self.edr_version), "INFO")

        self.system_novelty_threshold = edr_config.system_novelty_threshold()
        self.place_novelty_threshold = edr_config.place_novelty_threshold()
        self.ship_novelty_threshold = edr_config.ship_novelty_threshold()
        self.cognitive_novelty_threshold = edr_config.cognitive_novelty_threshold()
        self.intel_even_if_clean = edr_config.intel_even_if_clean()
        
        self.edr_needs_u_novelty_threshold = edr_config.edr_needs_u_novelty_threshold()
        self.previous_ad = None

        self.blips_cache = lrucache.LRUCache(edr_config.lru_max_size(), edr_config.blips_max_age())
        self.cognitive_blips_cache = lrucache.LRUCache(edr_config.lru_max_size(), edr_config.blips_max_age())
        self.traffic_cache = lrucache.LRUCache(edr_config.lru_max_size(),
                                               edr_config.traffic_max_age())
        self.scans_cache = lrucache.LRUCache(edr_config.lru_max_size(), edr_config.scans_max_age())
        self.cognitive_scans_cache = lrucache.LRUCache(edr_config.lru_max_size(), edr_config.blips_max_age())

        self._email = tk.StringVar(value=config.get("EDREmail"))
        self._password = tk.StringVar(value=config.get("EDRPassword"))
        # Translators: this is shown on the EDMC's status line
        self._status = tk.StringVar(value=_(u"not authenticated."))
        self.status_ui = None

        visual = 1 if config.get("EDRVisualFeedback") == "True" else 0
        self._visual_feedback = tk.IntVar(value=visual)

        audio = 1 if config.get("EDRAudioFeedback") == "True" else 0
        self._audio_feedback = tk.IntVar(value=audio)

        self.player = edentities.EDCmdr()
        self.server = edrserver.EDRServer()
        
        self.edrsystems = edrsystems.EDRSystems(self.server)
        self.edrcmdrs = edrcmdrs.EDRCmdrs(self.server)
        self.edroutlaws = edroutlaws.EDROutlaws(self.server)
        self.edrlegal = edrlegalrecords.EDRLegalRecords(self.server)

        self.mandatory_update = False
        self.crimes_reporting = True
        self.motd = []
        self.tips = randomtips.RandomTips()
        self.help_content = helpcontent.HelpContent()

    def loud_audio_feedback(self):
        config.set("EDRAudioFeedbackVolume", "loud")
        self.AUDIO_FEEDBACK.loud()
        # Translators: this is shown on EDMC's status bar when a user enables loud audio cues
        self.status = _(u"loud audio cues.")

    def soft_audio_feedback(self):
        config.set("EDRAudioFeedbackVolume", "soft")
        self.AUDIO_FEEDBACK.soft()
        # Translators: this is shown on EDMC's status bar when a user enables soft audio cues
        self.status = _(u"soft audio cues.")

    def apply_config(self):
        c_email = config.get("EDREmail")
        c_password = config.get("EDRPassword")
        c_visual_feedback = config.get("EDRVisualFeedback")
        c_audio_feedback = config.get("EDRAudioFeedback")
        c_audio_volume = config.get("EDRAudioFeedbackVolume")

        if c_email is None:
            self._email.set("")
        else:
            self._email.set(c_email)

        if c_password is None:
            self._password.set("")
        else:
            self._password.set(c_password)

        if c_visual_feedback is None or c_visual_feedback == "False":
            self._visual_feedback.set(0)
        else:
            self._visual_feedback.set(1)

        if c_audio_feedback is None or c_audio_feedback == "False":
            self._audio_feedback.set(0)
        else:
            self._audio_feedback.set(1)

        if c_audio_volume is None or c_audio_volume == "loud":
            self.loud_audio_feedback()
        else:
            self.soft_audio_feedback()


    def check_version(self):
        version_range = self.server.server_version()
        self.motd = _edr(version_range["l10n_motd"])

        if version_range is None:
            # Translators: this is shown on EDMC's status bar when the version check fails
            self.status = _(u"check for version update has failed.")
            return

        if self.is_obsolete(version_range["min"]):
            EDRLOG.log(u"Mandatory update! {version} vs. {min}"
                       .format(version=self.edr_version, min=version_range["min"]), "ERROR")
            self.mandatory_update = True
            self.__status_update_pending()
        elif self.is_obsolete(version_range["latest"]):
            EDRLOG.log(u"EDR update available! {version} vs. {latest}"
                       .format(version=self.edr_version, latest=version_range["latest"]), "INFO")
            self.mandatory_update = False
            self.__status_update_pending()

    def is_obsolete(self, advertised_version):
        client_parts = map(int, self.edr_version.split('.'))
        advertised_parts = map(int, advertised_version.split('.'))
        return client_parts < advertised_parts

    @property
    def email(self):
        return self._email.get()

    @email.setter
    def email(self, new_email):
        self._email.set(new_email)

    @property
    def password(self):
        return self._password.get()

    @password.setter
    def password(self, new_password):
        self._password.set(new_password)

    @property
    def status(self):
        return self._status.get()

    @status.setter
    def status(self, new_status):
        self._status.set(new_status)
        if self.status_ui:
            self.status_ui.url = None
            self.status_ui.underline = False

    @property
    def visual_feedback(self):
        return self._visual_feedback.get() == 1

    @visual_feedback.setter
    def visual_feedback(self, new_value):
        self._visual_feedback.set(new_value)

    @property
    def audio_feedback(self):
        return self._audio_feedback.get() == 1

    @audio_feedback.setter
    def audio_feedback(self, new_value):
        self._audio_feedback.set(new_value)

    def player_name(self, name):
        self.edrcmdrs.inara.cmdr_name = name
        self.player.name = name

    def login(self):
        self.server.logout()
        if self.server.login(self.email, self.password):
            # Translators: this is shown on EDMC's status bar when the authentication succeeds
            self.status = _(u"authenticated.")
            return True
        # Translators: this is shown on EDMC's status bar when the authentication fails
        self.status = _(u"not authenticated.")
        return False

    def is_logged_in(self):
        return self.server.is_authenticated()

    def is_anonymous(self):
        return (self.is_logged_in() and self.server.is_anonymous())

    def warmup(self):
        EDRLOG.log(u"Warming up client.", "INFO")
        # Translators: this is shown when EDR warms-up via the overlay
        details = [_(u"Feeling lost? Send !help via the in-game chat")]
        if self.mandatory_update:
            # Translators: this is shown when EDR warms-up via the overlay if there is a mandatory update pending
            details = [_(u"Mandatory update!")]
        details += self.motd
        # Translators: this is shown when EDR warms-up via the overlay, the -- are for presentation purpose
        details.append(_(u"-- Random Tip --"))
        details.append(self.tips.tip())
        # Translators: this is shown when EDR warms-up via the overlay
        self.__notify(_(u"EDR v{} by LeKeno (Cobra Kai)").format(self.edr_version), details, clear_before=True)

    def shutdown(self):
        self.edrcmdrs.persist()
        self.edrsystems.persist()
        self.edroutlaws.persist()
        self.edrlegal.persist()
        self.server.logout()
        self.IN_GAME_MSG.shutdown()

    def app_ui(self, parent):
        label = tk.Label(parent, text=u"EDR:")
        self.status_ui = ttkHyperlinkLabel.HyperlinkLabel(parent, textvariable=self._status, anchor=tk.W)
        self.check_version()
        return (label, self.status_ui)

    def prefs_ui(self, parent):
        frame = notebook.Frame(parent)
        frame.columnconfigure(1, weight=1)

        # Translators: this is shown in the preferences panel
        ttkHyperlinkLabel.HyperlinkLabel(frame, text=_(u"EDR website"), background=notebook.Label().cget('background'), url="https://github.com/lekeno/edr/", underline=True).grid(padx=10, sticky=tk.W)       

        # Translators: this is shown in the preferences panel
        notebook.Label(frame, text=_(u'Credentials')).grid(padx=10, sticky=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=2, sticky=tk.EW)
        # Translators: this is shown in the preferences panel
        cred_label = notebook.Label(frame, text=_(u'Log in with your EDR account for full access'))
        cred_label.grid(padx=10, columnspan=2, sticky=tk.W)

        notebook.Label(frame, text=_(u"Email")).grid(padx=10, row=11, sticky=tk.W)
        notebook.Entry(frame, textvariable=self._email).grid(padx=10, row=11,
                                                             column=1, sticky=tk.EW)

        notebook.Label(frame, text=_(u"Password")).grid(padx=10, row=12, sticky=tk.W)
        notebook.Entry(frame, textvariable=self._password,
                       show=u'*').grid(padx=10, row=12, column=1, sticky=tk.EW)

        # Translators: this is shown in the preferences panel as a heading for feedback options (e.g. overlay, audio cues)
        notebook.Label(frame, text=_(u"EDR Feedback:")).grid(padx=10, row=14, sticky=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=2, sticky=tk.EW)
        
        notebook.Checkbutton(frame, text=_(u"Overlay"),
                             variable=self._visual_feedback).grid(padx=10, row=16,
                                                                  sticky=tk.W)
        notebook.Checkbutton(frame, text=_(u"Sound"),
                             variable=self._audio_feedback).grid(padx=10, row=17, sticky=tk.W)
        
        if self.server.is_authenticated():
            self.status = _(u"authenticated.")
        else:
            self.status = _(u"not authenticated.")

        return frame

    def __status_update_pending(self):
        # Translators: this is shown in EDMC's status
        self.status = _(u"mandatory EDR update!") if self.mandatory_update else _(u"please update EDR!")
        if self.status_ui:
            self.status_ui.underline = True
            self.status_ui.url = "https://github.com/lekeno/edr/releases/latest"
            

    def prefs_changed(self):
        set_language(config.get("language"))
        if self.mandatory_update:
            EDRLOG.log(u"Out-of-date client, aborting.", "ERROR")
            self.__status_update_pending()
            return

        config.set("EDREmail", self.email)
        config.set("EDRPassword", self.password)
        config.set("EDRVisualFeedback", "True" if self.visual_feedback else "False")
        config.set("EDRAudioFeedback", "True" if self.audio_feedback else "False")
        EDRLOG.log(u"Audio cues: {}, {}".format(config.get("EDRAudioFeedback"),
                                                config.get("EDRAudioFeedbackVolume")), "DEBUG")
        self.login()

    def check_system(self, star_system):
        EDRLOG.log(u"Check system called: {}".format(star_system), "INFO")
        details = []
        notams = self.edrsystems.active_notams(star_system)
        if notams:
            EDRLOG.log(u"NOTAMs for {}: {}".format(star_system, notams), "DEBUG")
            details += notams
        
        if self.edrsystems.has_sitrep(star_system):
            if star_system == self.player.star_system and self.player.in_bad_neighborhood():
                EDRLOG.log(u"Sitrep system is known to be an anarchy. Crimes aren't reported.", "INFO")
                # Translators: this is shown via the overlay if the system of interest is an Anarchy (current system or !sitrep <system>)
                details.append(_c(u"Sitrep|Anarchy: not all crimes are reported."))
            if self.edrsystems.has_recent_activity(star_system):
                summary = self.edrsystems.summarize_recent_activity(star_system)
                for section in summary:
                    details.append(u"{}: {}".format(section, "; ".join(summary[section])))
        if details:
            # Translators: this is the heading for the sitrep of a given system {}; shown via the overlay
            self.__sitrep(_(u"SITREP for {}").format(star_system), details)

    def notams(self):
        summary = self.edrsystems.systems_with_active_notams()
        if summary:
            details = []
            # Translators: this shows a ist of systems {} with active NOtice To Air Men via the overlay
            details.append(_(u"Active NOTAMs for: {}").format("; ".join(summary)))
            # Translators: this is the heading for the active NOTAMs overlay
            self.__sitrep(_(u"NOTAMs"), details)
        else:
            self.__sitrep(_(u"NOTAMs"), [_(u"No active NOTAMs.")])

    def notam(self, star_system):
        summary = self.edrsystems.active_notams(star_system)
        if summary:
            EDRLOG.log(u"NOTAMs for {}: {}".format(star_system, summary), "DEBUG")
            # Translators: this is the heading to show any active NOTAM for a given system {} 
            self.__sitrep(_(u"NOTAM for {}").format(star_system), summary)
        else:
            self.__sitrep(_(u"NOTAM for {}").format(star_system), [_(u"No active NOTAMs.")])

    def sitreps(self):
        details = []
        summary = self.edrsystems.systems_with_recent_activity()
        for section in summary:
            details.append(u"{}: {}".format(section, "; ".join(summary[section])))
        if details:
            self.__sitrep(_(u"SITREPS"), details)


    def cmdr_id(self, cmdr_name):
        profile = self.cmdr(cmdr_name, check_inara_server=False)
        if not (profile is None or profile.cid is None):
            EDRLOG.log(u"Cmdr {cmdr} known as id={cid}".format(cmdr=cmdr_name,
                                                               cid=profile.cid), "DEBUG")
            return profile.cid

        EDRLOG.log(u"Failed to retrieve/create cmdr {}".format(cmdr_name), "ERROR")
        return None

    def cmdr(self, cmdr_name, autocreate=True, check_inara_server=False):
        return self.edrcmdrs.cmdr(cmdr_name, autocreate, check_inara_server)

    def evict_system(self, star_system):
        self.edrsystems.evict(star_system)

    def evict_cmdr(self, cmdr):
        self.edrcmdrs.evict(cmdr)

    def __novel_enough_situation(self, new, old, cognitive = False):
        if old is None:
            return True

        delta = new["timestamp"] - old["timestamp"]
        
        if cognitive:
            return (new["starSystem"] != old["starSystem"] or new["place"] != old["place"]) or delta > self.cognitive_novelty_threshold

        if new["starSystem"] != old["starSystem"]:
            return delta > self.system_novelty_threshold

        if new["place"] != old["place"]:
            return (old["place"] == "" or
                    old["place"] == "Unknown" or
                    delta > self.place_novelty_threshold)

        if new["ship"] != old["ship"]:
            return (old["ship"] == "" or
                    old["ship"] == "Unknown" or
                    delta > self.ship_novelty_threshold)

    def novel_enough_blip(self, cmdr_id, blip, cognitive = False):
        last_blip = self.cognitive_blips_cache.get(cmdr_id) if cognitive else self.blips_cache.get(cmdr_id)
        return self.__novel_enough_situation(blip, last_blip, cognitive)

    def novel_enough_scan(self, cmdr_id, scan, cognitive = False):
        last_scan = self.cognitive_scans_cache.get(cmdr_id) if cognitive else self.scans_cache.get(cmdr_id)
        novel_situation = self.__novel_enough_situation(scan, last_scan, cognitive)
        return novel_situation or (scan["wanted"] != last_scan["wanted"]) or (scan["bounty"] != last_scan["bounty"])

    def novel_enough_traffic_report(self, sighted_cmdr, report):
        last_report = self.traffic_cache.get(sighted_cmdr)
        return self.__novel_enough_situation(report, last_report)

    def who(self, cmdr_name, autocreate=False):
        profile = self.cmdr(cmdr_name, autocreate, check_inara_server=True)
        if not profile is None:
            self.status = _(u"got info about {}").format(cmdr_name)
            EDRLOG.log(u"Who {} : {}".format(cmdr_name, profile.short_profile()), "INFO")
            legal = self.edrlegal.summarize_recents(profile.cid)
            if legal:
                self.__intel(cmdr_name, [profile.short_profile(), legal])
            else:
                self.__intel(cmdr_name, [profile.short_profile()])
        else:
            EDRLOG.log(u"Who {} : no info".format(cmdr_name), "INFO")
            self.__intel(cmdr_name, ["No info about {}".format(cmdr_name)])

    def blip(self, cmdr_name, blip):
        cmdr_id = self.cmdr_id(cmdr_name)
        if cmdr_id is None:
            self.status = u"no cmdr id (contact)."
            EDRLOG.log(u"Can't submit blip (no cmdr id for {}).".format(cmdr_name), "ERROR")
            return

        profile = self.cmdr(cmdr_name)
        if profile and (self.player.name != cmdr_name) and profile.is_dangerous():
            self.status = u"{} is bad news.".format(cmdr_name)
            if self.novel_enough_blip(cmdr_id, blip, cognitive = True):
                self.__warning(u"Warning!", [profile.short_profile()])
                self.cognitive_blips_cache.set(cmdr_id, blip)
                if self.is_anonymous():
                    self.advertise_full_account("You could have helped other EDR users by reporting this outlaw.")
            else:
                EDRLOG.log("Skipping warning since a warning was recently shown.", "INFO")

        if not self.novel_enough_blip(cmdr_id, blip):
            self.status = u"skipping blip (not novel enough)."
            EDRLOG.log(u"Blip is not novel enough to warrant reporting", "INFO")
            return True

        if self.is_anonymous():
            EDRLOG.log("Skipping blip since the user is anonymous.", "INFO")
            self.blips_cache.set(cmdr_id, blip)
            return False

        success = self.server.blip(cmdr_id, blip)
        if success:
            self.status = u"blip reported for {}.".format(cmdr_name)
            self.blips_cache.set(cmdr_id, blip)

        return success

    def scanned(self, cmdr_name, scan):
        cmdr_id = self.cmdr_id(cmdr_name)
        if cmdr_id is None:
            self.status = _(u"cmdr unknown to EDR.")
            EDRLOG.log(u"Can't submit scan (no cmdr id for {}).".format(cmdr_name), "ERROR")
            return

        if self.novel_enough_scan(cmdr_id, scan, cognitive = True):
            profile = self.cmdr(cmdr_name)
            legal = self.edrlegal.summarize_recents(profile.cid)
            bounty = edentities.EDBounty(scan["bounty"]) if scan["bounty"] else None
            if profile and (self.player.name != cmdr_name):
                if profile.is_dangerous():
                    # Translators: this is shown via EDMC's EDR status line upon contact with a known outlaw
                    self.status = _(u"{} is bad news.").format(cmdr_name)
                    details = [profile.short_profile()]
                    if bounty:
                        details.append(_(u"Wanted for {} cr").format(edentities.EDBounty(scan["bounty"]).pretty_print()))
                    elif scan["wanted"]:
                        details.append(_(u"Wanted somewhere. A Kill-Warrant-Scan will reveal their highest bounty."))
                    if legal:
                        details.append(legal)
                    self.__warning(_(u"Warning!"), details)
                elif self.intel_even_if_clean or (scan["wanted"] and bounty.is_significant()):
                    self.status = _(u"Intel for cmdr {}.").format(cmdr_name)
                    details = [profile.short_profile()]
                    if bounty:
                        details.append(_(u"Wanted for {} cr").format(edentities.EDBounty(scan["bounty"]).pretty_print()))
                    elif scan["wanted"]:
                        details.append(_(u"Wanted somewhere but it could be minor offenses."))
                    if legal:
                        details.append(legal)
                    self.__intel(_(u"Intel"), details)
                if (self.is_anonymous() and (profile.is_dangerous() or (scan["wanted"] and bounty.is_significant()))):
                    # Translators: this is shown to users who don't yet have an EDR account
                    self.advertise_full_account(_(u"You could have helped other EDR users by reporting this outlaw!"))
                self.cognitive_scans_cache.set(cmdr_id, scan)

        if not self.novel_enough_scan(cmdr_id, scan):
            self.status = _(u"not novel enough (scan).")
            EDRLOG.log(u"Scan is not novel enough to warrant reporting", "INFO")
            return True

        if self.is_anonymous():
            EDRLOG.log("Skipping reporting scan since the user is anonymous.", "INFO")
            self.scans_cache.set(cmdr_id, scan)
            return False

        success = self.server.scanned(cmdr_id, scan)
        if success:
            self.status = _(u"scan reported for {}.").format(cmdr_name)
            self.scans_cache.set(cmdr_id, scan)

        return success        


    def traffic(self, star_system, traffic):
        if self.is_anonymous():
            EDRLOG.log(u"Skipping traffic report since the user is anonymous.", "INFO")
            return False

        sigthed_cmdr = traffic["cmdr"]
        if not self.novel_enough_traffic_report(sigthed_cmdr, traffic):
            self.status = _(u"not novel enough (traffic).")
            EDRLOG.log(u"Traffic report is not novel enough to warrant reporting", "INFO")
            return True

        sid = self.edrsystems.system_id(star_system, may_create=True)
        if sid is None:
            EDRLOG.log(u"Failed to report traffic for system {} : no id found.".format(star_system),
                       "DEBUG")
            return False

        success = self.server.traffic(sid, traffic)
        if success:
            self.status = _(u"traffic reported.")
            self.traffic_cache.set(sigthed_cmdr, traffic)

        return success


    def crime(self, star_system, crime):
        if not self.crimes_reporting:
            EDRLOG.log(u"Crimes reporting is off (!crimes on to re-enable).", "INFO")
            self.status = _(u"Crimes reporting is off (!crimes on to re-enable)")
            return False
            
        if self.player.in_bad_neighborhood():
            EDRLOG.log(u"Crime not being reported because the player is in an anarchy.", "INFO")
            self.status = _(u"Anarchy system (crimes not reported).")
            return False

        if self.is_anonymous():
            EDRLOG.log(u"Skipping crime report since the user is anonymous.", "INFO")
            if crime["victim"] == self.player.name:
                self.advertise_full_account(_(u"You could have helped other EDR users or get help by reporting this crime!"))
            return False

        sid = self.edrsystems.system_id(star_system, may_create=True)
        if sid is None:
            EDRLOG.log(u"Failed to report crime in system {} : no id found.".format(star_system),
                       "DEBUG")
            return False

        return self.server.crime(sid, crime)

    def tag_cmdr(self, cmdr_name, tag):
        if self.is_anonymous():
            EDRLOG.log(u"Skipping tag cmdr since the user is anonymous.", "INFO")
            self.advertise_full_account(_(u"Sorry, this feature only works with an EDR account."), passive=False)
            return False

        success = self.edrcmdrs.tag_cmdr(cmdr_name, tag)
        if success:
            self.__notify(_(u"Cmdr Dex"), [_(u"Successfully tagged cmdr {name} with {tag}").format(name=cmdr_name, tag=tag)])
        else:
            self.__notify(_(u"Cmdr Dex"), [_(u"Could not tag cmdr {name} with {tag}").format(name=cmdr_name, tag=tag)])
        return success
    
    def memo_cmdr(self, cmdr_name, memo):
        if self.is_anonymous():
            EDRLOG.log(u"Skipping memo cmdr since the user is anonymous.", "INFO")
            self.advertise_full_account(_(u"Sorry, this feature only works with an EDR account."), passive=False)
            return False

        success = self.edrcmdrs.memo_cmdr(cmdr_name, memo)
        if success:
            self.__notify(_(u"Cmdr Dex"), [_(u"Successfully attached a memo to cmdr {}").format(cmdr_name)])
        else:
            self.__notify(_(u"Cmdr Dex"), [_(u"Failed to attach a memo to cmdr {}").format(cmdr_name)])       
        return success

    def clear_memo_cmdr(self, cmdr_name):
        if self.is_anonymous():
            EDRLOG.log(u"Skipping clear_memo_cmdr since the user is anonymous.", "INFO")
            self.advertise_full_account(_(u"Sorry, this feature only works with an EDR account."), passive=False)
            return False

        success = self.edrcmdrs.clear_memo_cmdr(cmdr_name)
        if success:
            self.__notify(_(u"Cmdr Dex"),[_(u"Successfully removed memo from cmdr {}").format(cmdr_name)])
        else:
            self.__notify(_(u"Cmdr Dex"), [_(u"Failed to remove memo from cmdr {}").format(cmdr_name)])        
        return success

    def untag_cmdr(self, cmdr_name, tag):
        if self.is_anonymous():
            EDRLOG.log(u"Skipping untag cmdr since the user is anonymous.", "INFO")
            self.advertise_full_account(_(u"Sorry, this feature only works with an EDR account."), passive=False)
            return False

        success = self.edrcmdrs.untag_cmdr(cmdr_name, tag)
        if success:
            if tag is None:
                self.__notify(_(u"Cmdr Dex"), [_(u"Successfully removed all tags from cmdr {}").format(cmdr_name)])
            else:
                self.__notify(_(u"Cmdr Dex"), [_(u"Successfully removed tag {} from cmdr {}").format(tag, cmdr_name)])
        else:
            self.__notify(_(u"Cmdr Dex"), [_(u"Could not remove tag(s) from cmdr {}").format(cmdr_name)])
        return success

    def where(self, cmdr_name):
        report = self.edroutlaws.where(cmdr_name)
        if report:
            self.status = _(u"got info about {}").format(cmdr_name)
            self.__intel(_(u"Intel for {}").format(cmdr_name), report)
        else:
            EDRLOG.log(u"Where {} : no info".format(cmdr_name), "INFO")
            self.status = _(u"no info about {}").format(cmdr_name)
            self.__intel(_(u"Intel for {}").format(cmdr_name), [_(u"Not recently sighted or not an outlaw.")])

    def outlaws(self):
        outlaws_report = self.edroutlaws.recent_sightings()
        if not outlaws_report:
            EDRLOG.log(u"No recently sighted outlaws", "INFO")
            self.__sitrep(_(u"Recently Sighted Outlaws"), [_(u"No outlaws sighted in the last {}").format(edtime.EDTime.pretty_print_timespan(self.edroutlaws.timespan))])
            return False
        
        self.status = _(u"recently sighted outlaws")
        EDRLOG.log(u"Got recently sighted outlaws", "INFO")
        self.__sitrep(_(u"Recently Sighted Outlaws"), outlaws_report)

    def help(self, section):
        content = self.help_content.get(section)
        if not content:
            return False

        EDRLOG.log(u"Show help for {} with header: {} and details: {}".format(section, content["header"], content["details"][0]), "DEBUG")
        self.IN_GAME_MSG.help(content["header"], content["details"])
        return True

    def clear(self):
        self.IN_GAME_MSG.clear()
           

    def __sitrep(self, header, details):
        if self.audio_feedback:
            self.AUDIO_FEEDBACK.notify()
        if not self.visual_feedback:
            return
        EDRLOG.log(u"sitrep with header: {}; details: {}".format(header, details[0]), "DEBUG")
        self.IN_GAME_MSG.clear_sitrep()
        self.IN_GAME_MSG.sitrep(header, details)

    def __intel(self, who, details, clear_before=False):
        if self.audio_feedback:
            self.AUDIO_FEEDBACK.notify()
        if not self.visual_feedback:
            return
        EDRLOG.log(u"Intel for {}; details: {}".format(who, details[0]), "DEBUG")
        if clear_before:
            self.IN_GAME_MSG.clear_intel()
        self.IN_GAME_MSG.intel(_(u"Intel"), details)

    def __warning(self, header, details, clear_before=False):
        if self.audio_feedback:
            self.AUDIO_FEEDBACK.warn()
        if not self.visual_feedback:
            return
        EDRLOG.log(u"Warning; details: {}".format(details[0]), "DEBUG")
        if clear_before:
            self.IN_GAME_MSG.clear_warning()
        self.IN_GAME_MSG.warning(header, details)
    
    def __notify(self, header, details, clear_before=False):
        if self.audio_feedback:
            self.AUDIO_FEEDBACK.notify()
        if not self.visual_feedback:
            return
        EDRLOG.log(u"Notify about {}; details: {}".format(header, details[0]), "DEBUG")
        if clear_before:
            self.IN_GAME_MSG.clear_notice()
        self.IN_GAME_MSG.notify(header, details)

    def notify_with_details(self, notice, details):
        self.__notify(notice, details)

    def warn_with_details(self, warning, details):
        self.__warning(warning, details)
    
    def advertise_full_account(self, context, passive=True):
        now = datetime.datetime.now()
        now_epoch = time.mktime(now.timetuple())            
        if passive and self.previous_ad:
            if (now_epoch - self.previous_ad) <= self.edr_needs_u_novelty_threshold:
                return False

        self.__notify(_(u"EDR needs you!"), [context, u"--", _(u"Apply for an account at https://lekeno.github.io/"), _(u"It's free, no strings attached.")], clear_before=True)
        self.previous_ad = now_epoch
        return True
