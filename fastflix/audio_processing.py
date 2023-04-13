# -*- coding: utf-8 -*-
from copy import deepcopy

from iso639 import Lang
from iso639.exceptions import InvalidLanguageValue
from box import Box

from fastflix.models.profiles import AudioMatch, MatchType, MatchItem


def apply_audio_filters(
    audio_filters: list[AudioMatch] | bool | None,
    original_tracks: list[Box],
):
    """
    The goal of this function is to take a set of audio_filters and figure out which tracks
    apply and what conversions to set.
    """
    if not audio_filters:
        return []

    original_tracks = deepcopy(original_tracks)

    tracks = []
    for audio_match in audio_filters:
        if audio_match.match_item == MatchItem.ALL:
            track_select = original_tracks.copy()
            if track_select:
                if audio_match.match_type == MatchType.FIRST:
                    track_select = [track_select[0]]
                elif audio_match.match_type == MatchType.LAST:
                    track_select = [track_select[-1]]
                for track in track_select:
                    tracks.append((track, audio_match))

        elif audio_match.match_item == MatchItem.TITLE:
            subset_tracks = []
            for track in original_tracks:
                if audio_match.match_input.lower() in track.tags.get("title", "").casefold():
                    subset_tracks.append((track, audio_match))
            if subset_tracks:
                if audio_match.match_type == MatchType.FIRST:
                    tracks.append(subset_tracks[0])
                elif audio_match.match_type == MatchType.LAST:
                    tracks.append(subset_tracks[-1])
                else:
                    tracks.extend(subset_tracks)

        elif audio_match.match_item == MatchItem.TRACK:
            for track in original_tracks:
                if track.index == int(audio_match.match_input):
                    tracks.append((track, audio_match))

        elif audio_match.match_item == MatchItem.LANGUAGE:
            subset_tracks = []
            for track in original_tracks:
                try:
                    if Lang(audio_match.match_input) == Lang(track.tags["language"]):
                        subset_tracks.append((track, audio_match))
                except (InvalidLanguageValue, KeyError):
                    pass
            if subset_tracks:
                if audio_match.match_type == MatchType.FIRST:
                    tracks.append(subset_tracks[0])
                elif audio_match.match_type == MatchType.LAST:
                    tracks.append(subset_tracks[-1])
                else:
                    tracks.extend(subset_tracks)

        elif audio_match.match_item == MatchItem.CHANNELS:
            subset_tracks = []
            for track in original_tracks:
                if int(audio_match.match_input) == track.channels:
                    subset_tracks.append((track, audio_match))
            if subset_tracks:
                if audio_match.match_type == MatchType.FIRST:
                    tracks.append(subset_tracks[0])
                elif audio_match.match_type == MatchType.LAST:
                    tracks.append(subset_tracks[-1])
                else:
                    tracks.extend(subset_tracks)

    return sorted(tracks, key=lambda x: x[0].index)
