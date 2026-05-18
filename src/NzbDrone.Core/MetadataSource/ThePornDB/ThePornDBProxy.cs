using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using NLog;
using NzbDrone.Common.Extensions;
using NzbDrone.Common.Http;
using NzbDrone.Common.Serializer;
using NzbDrone.Core.Configuration;
using NzbDrone.Core.Exceptions;
using NzbDrone.Core.MediaCover;
using NzbDrone.Core.Parser;
using NzbDrone.Core.MetadataSource.SkyHook;
using NzbDrone.Core.Tv;
using Newtonsoft.Json.Linq;

namespace NzbDrone.Core.MetadataSource.ThePornDB
{
    public interface IThePornDBProxy
    {
        Tuple<Series, List<Episode>> GetSeriesInfo(int tvdbSeriesId);
        List<Series> SearchForNewSeries(string title);
    }

    public class ThePornDBProxy : IThePornDBProxy
    {
        private readonly IHttpClient _httpClient;
        private readonly Logger _logger;
        private readonly IConfigFileProvider _configFileProvider;

        private const string TPDB_URL = "https://theporndb.net/graphql";

        public ThePornDBProxy(IHttpClient httpClient,
                              IConfigFileProvider configFileProvider,
                              Logger logger)
        {
            _httpClient = httpClient;
            _configFileProvider = configFileProvider;
            _logger = logger;
        }

        public Tuple<Series, List<Episode>> GetSeriesInfo(int tvdbSeriesId)
        {
            _logger.Debug("Fetching studio info from ThePornDB for ID: {0}", tvdbSeriesId);

            var query = @"
            query FindStudio($id: ID!) {
              findStudio(id: $id) {
                id
                name
                image_url
                parent_studio { id name }
                scenes {
                  id
                  title
                  date
                  image_url
                  duration
                  synopsis
                  performers { name }
                }
              }
            }";

            var request = new HttpRequestBuilder(TPDB_URL)
                .Accept(HttpAccept.Json)
                .Post()
                .Build();

            request.Headers.ContentType = "application/json";
            request.SetContent(new
            {
                query = query,
                variables = new { id = tvdbSeriesId }
            }.ToJson());

            var response = _httpClient.Execute(request);
            if (response.StatusCode != HttpStatusCode.OK)
            {
                throw new SkyHookException("Failed to fetch from ThePornDB: " + response.StatusCode);
            }

            var data = JObject.Parse(response.Content);
            var studioData = data["data"]?["findStudio"];

            if (studioData == null)
            {
                throw new SeriesNotFoundException(tvdbSeriesId);
            }

            var series = MapSeries(studioData);
            var episodes = studioData["scenes"]?.Select(MapEpisode).ToList() ?? new List<Episode>();

            return new Tuple<Series, List<Episode>>(series, episodes);
        }

        public List<Series> SearchForNewSeries(string title)
        {
            _logger.Debug("Searching ThePornDB for: {0}", title);

            var query = @"
            query FindStudios($name: String!) {
              findStudios(input: { name: $name }) {
                studios {
                  id
                  name
                  image_url
                }
              }
            }";

            var request = new HttpRequestBuilder(TPDB_URL)
                .Accept(HttpAccept.Json)
                .Post()
                .Build();

            request.Headers.ContentType = "application/json";
            request.SetContent(new
            {
                query = query,
                variables = new { name = title }
            }.ToJson());

            var response = _httpClient.Execute(request);
            var data = JObject.Parse(response.Content);
            var studios = data["data"]?["findStudios"]?["studios"];

            if (studios == null) return new List<Series>();

            return studios.Select(MapSeries).ToList();
        }

        private Series MapSeries(JToken studio)
        {
            var series = new Series();
            series.TvdbId = studio["id"].Value<int>();
            series.Title = studio["name"].Value<string>();
            series.CleanTitle = series.Title.CleanSeriesTitle();
            series.SortTitle = series.Title.CleanSeriesTitle();
            series.Status = SeriesStatusType.Continuing;
            series.Overview = "Studio tracked via ThePornDB";
            series.Network = studio["parent_studio"]?["name"]?.Value<string>() ?? series.Title;
            
            var imageUrl = studio["image_url"]?.Value<string>();
            if (imageUrl.IsNotNullOrWhiteSpace())
            {
                series.Images.Add(new MediaCover.MediaCover(MediaCoverTypes.Poster, imageUrl));
            }

            return series;
        }

        private Episode MapEpisode(JToken scene)
        {
            var episode = new Episode();
            episode.ExternalId = scene["id"].Value<string>();
            episode.Title = scene["title"]?.Value<string>() ?? "Untitled Scene";
            episode.Overview = scene["synopsis"]?.Value<string>();
            
            var dateStr = scene["date"]?.Value<string>();
            if (DateTime.TryParse(dateStr, out var date))
            {
                episode.AirDate = date.ToString("yyyy-MM-dd");
                episode.AirDateUtc = date;
                episode.SeasonNumber = date.Year;
            }
            else
            {
                episode.SeasonNumber = 1;
            }

            episode.Runtime = (int)(scene["duration"]?.Value<double>() / 60 ?? 0);
            
            var imageUrl = scene["image_url"]?.Value<string>();
            if (imageUrl.IsNotNullOrWhiteSpace())
            {
                episode.Images.Add(new MediaCover.MediaCover(MediaCoverTypes.Screenshot, imageUrl));
            }

            return episode;
        }
    }
}
