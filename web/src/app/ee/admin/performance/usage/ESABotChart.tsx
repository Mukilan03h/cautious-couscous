import { ThreeDotsLoader } from "@/components/Loading";
import { getDatesList, useESABotAnalytics } from "../lib";
import { DateRangePickerValue } from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import Text from "@/components/ui/text";
import Title from "@/components/ui/title";
import CardSection from "@/components/admin/CardSection";
import { AreaChartDisplay } from "@/components/ui/areaChart";

export function ESABotChart({
  timeRange,
}: {
  timeRange: DateRangePickerValue;
}) {
  const {
    data: esaBotAnalyticsData,
    isLoading: isESABotAnalyticsLoading,
    error: esaBotAnalyticsError,
  } = useESABotAnalytics(timeRange);

  let chart;
  if (isESABotAnalyticsLoading) {
    chart = (
      <div className="h-80 flex flex-col">
        <ThreeDotsLoader />
      </div>
    );
  } else if (
    !esaBotAnalyticsData ||
    esaBotAnalyticsData[0] == undefined ||
    esaBotAnalyticsError
  ) {
    chart = (
      <div className="h-80 text-red-600 text-bold flex flex-col">
        <p className="m-auto">Failed to fetch feedback data...</p>
      </div>
    );
  } else {
    const initialDate =
      timeRange.from || new Date(esaBotAnalyticsData[0].date);
    const dateRange = getDatesList(initialDate);

    const dateToESABotAnalytics = new Map(
      esaBotAnalyticsData.map((esaBotAnalyticsEntry) => [
        esaBotAnalyticsEntry.date,
        esaBotAnalyticsEntry,
      ])
    );

    chart = (
      <AreaChartDisplay
        className="mt-4"
        data={dateRange.map((dateStr) => {
          const esaBotAnalyticsForDate = dateToESABotAnalytics.get(dateStr);
          return {
            Day: dateStr,
            "Total Queries": esaBotAnalyticsForDate?.total_queries || 0,
            "Automatically Resolved":
              esaBotAnalyticsForDate?.auto_resolved || 0,
          };
        })}
        categories={["Total Queries", "Automatically Resolved"]}
        index="Day"
        colors={["indigo", "fuchsia"]}
        yAxisWidth={60}
      />
    );
  }

  return (
    <CardSection className="mt-8">
      <Title>Slack Channel</Title>
      <Text>Total Queries vs Auto Resolved</Text>
      {chart}
    </CardSection>
  );
}
